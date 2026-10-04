from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from hydra_governed_intelligence import (
    load_evidence,
    load_grounding_policy,
    load_policy,
    load_retrieval_policy,
    run_evaluation,
    run_grounding_evaluation,
    run_retrieval_evaluation,
)
from hydra_governed_intelligence.pre_upload_verifier import (
    BUNDLE_MEMBERS,
    ZIP_EXTERNAL_ATTR,
    ZIP_TIMESTAMP,
    VerificationError,
    _build_bundle_bytes,
    _snapshot_file,
    _snapshot_verification_inputs,
    _verify_bundle,
    main,
    package_repository_artifacts,
    verify_repository_artifacts,
)

from tests.support import ROOT, build_pipeline_outputs


class PreUploadVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._class_temp = tempfile.TemporaryDirectory(dir=ROOT)
        cls.addClassCleanup(cls._class_temp.cleanup)
        cls.baseline = Path(cls._class_temp.name) / "baseline"
        intelligence = cls.baseline / "governed-intelligence-sample"
        pipeline = cls.baseline / "market-data-pipeline-sample" / "build" / "demo"

        shutil.copytree(ROOT / "config", intelligence / "config")
        shutil.copytree(ROOT / "fixtures", intelligence / "fixtures")
        build_pipeline_outputs(pipeline)

        evidence = load_evidence(pipeline)
        context_policy = load_policy(intelligence / "config" / "policy.json")
        retrieval_policy = load_retrieval_policy(
            intelligence / "config" / "retrieval_policy.json"
        )
        grounding_policy = load_grounding_policy(
            intelligence / "config" / "grounding_policy.json"
        )
        run_evaluation(
            cases_path=intelligence / "fixtures" / "evaluation_cases.json",
            evidence=evidence,
            policy=context_policy,
            output_dir=intelligence / "build" / "evaluation",
        )
        run_retrieval_evaluation(
            cases_path=intelligence / "fixtures" / "retrieval_cases.json",
            qrels_path=intelligence / "fixtures" / "retrieval_qrels.json",
            evidence=evidence,
            policy=retrieval_policy,
            output_dir=intelligence / "build" / "retrieval",
        )
        run_grounding_evaluation(
            cases_path=intelligence / "fixtures" / "grounding_cases.json",
            evidence=evidence,
            retrieval_policy=retrieval_policy,
            grounding_policy=grounding_policy,
            output_dir=intelligence / "build" / "grounding",
        )

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp_dir.cleanup)
        self.repository = Path(self.temp_dir.name) / "repository"
        shutil.copytree(self.baseline, self.repository)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def _rehash_manifest_output(
        self,
        output_dir: Path,
        manifest_name: str,
        output_key: str,
        output_path: Path,
    ) -> None:
        manifest_path = output_dir / manifest_name
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"][output_key]["sha256"] = hashlib.sha256(
            output_path.read_bytes()
        ).hexdigest()
        self._write_json(manifest_path, manifest)

    def test_complete_artifact_set_passes(self) -> None:
        summary = verify_repository_artifacts(self.repository)

        self.assertEqual(summary.manifest_outputs, 9)
        self.assertEqual(summary.receipts, 26)

    def test_deterministic_bundle_is_byte_identical(self) -> None:
        first_path = self.repository / "artifacts" / "first.zip"
        second_path = self.repository / "artifacts" / "second.zip"

        first = package_repository_artifacts(self.repository, first_path)
        second = package_repository_artifacts(self.repository, second_path)
        first_bytes = first_path.read_bytes()
        second_bytes = second_path.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first.bundle_members, 13)
        self.assertEqual(first.bundle_members, len(BUNDLE_MEMBERS))
        self.assertEqual(first.bundle_bytes, len(first_bytes))
        self.assertEqual(first.bundle_sha256, hashlib.sha256(first_bytes).hexdigest())
        self.assertEqual(first, second)

    def test_bundle_member_metadata_and_payloads_are_exact(self) -> None:
        bundle_path = self.repository / "artifacts" / "proof.zip"
        snapshots = _snapshot_verification_inputs(self.repository)

        package_repository_artifacts(self.repository, bundle_path)

        with zipfile.ZipFile(bundle_path, mode="r") as archive:
            self.assertEqual(archive.comment, b"")
            self.assertEqual(archive.namelist(), list(BUNDLE_MEMBERS))
            for info in archive.infolist():
                self.assertEqual(info.date_time, ZIP_TIMESTAMP)
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.create_version, 20)
                self.assertEqual(info.extract_version, 20)
                self.assertEqual(info.flag_bits, 0)
                self.assertEqual(info.internal_attr, 0)
                self.assertEqual(info.external_attr, ZIP_EXTERNAL_ATTR)
                self.assertEqual(info.extra, b"")
                self.assertEqual(info.comment, b"")
                self.assertEqual(info.volume, 0)
                self.assertFalse(info.is_dir())
                self.assertEqual(archive.read(info), snapshots[info.filename])

    def test_source_mutation_after_snapshot_does_not_change_bundle(self) -> None:
        snapshots = _snapshot_verification_inputs(self.repository)
        expected_bundle = _build_bundle_bytes(snapshots)
        member_path = self.repository / Path(BUNDLE_MEMBERS[0])

        member_path.write_bytes(b"changed after snapshot\n")

        actual_bundle = _build_bundle_bytes(snapshots)
        self.assertEqual(actual_bundle, expected_bundle)
        self.assertEqual(_verify_bundle(actual_bundle, snapshots), {
            name: snapshots[name] for name in BUNDLE_MEMBERS
        })

    def test_bundle_payload_tampering_fails(self) -> None:
        snapshots = _snapshot_verification_inputs(self.repository)
        tampered = dict(snapshots)
        member = BUNDLE_MEMBERS[0]
        payload = bytearray(tampered[member])
        payload[0] ^= 1
        tampered[member] = bytes(payload)

        with self.assertRaisesRegex(VerificationError, "CRC changed"):
            _verify_bundle(_build_bundle_bytes(tampered), snapshots)

    def test_bundle_metadata_tampering_fails(self) -> None:
        snapshots = _snapshot_verification_inputs(self.repository)
        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
        ) as archive:
            for index, member in enumerate(BUNDLE_MEMBERS):
                timestamp = (1981, 1, 1, 0, 0, 0) if index == 0 else ZIP_TIMESTAMP
                info = zipfile.ZipInfo(member, date_time=timestamp)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.create_version = 20
                info.extract_version = 20
                info.external_attr = ZIP_EXTERNAL_ATTR
                archive.writestr(info, snapshots[member])

        with self.assertRaisesRegex(VerificationError, "timestamp changed"):
            _verify_bundle(buffer.getvalue(), snapshots)

    def test_packaging_failure_leaves_no_bundle_or_temporary_file(self) -> None:
        output_dir = (
            self.repository
            / "governed-intelligence-sample"
            / "build"
            / "evaluation"
        )
        manifest_path = output_dir / "output_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["decisions_jsonl"]["sha256"] = "0" * 64
        self._write_json(manifest_path, manifest)
        bundle_path = self.repository / "artifacts" / "proof.zip"

        with self.assertRaisesRegex(VerificationError, "SHA-256 mismatch"):
            package_repository_artifacts(self.repository, bundle_path)

        self.assertFalse(bundle_path.exists())
        self.assertEqual(list(bundle_path.parent.glob(f".{bundle_path.name}.*.tmp")), [])

    def test_failed_replacement_preserves_existing_bundle(self) -> None:
        bundle_path = self.repository / "artifacts" / "proof.zip"
        bundle_path.parent.mkdir(parents=True)
        bundle_path.write_bytes(b"existing bundle")
        (self.repository / Path(BUNDLE_MEMBERS[0])).unlink()

        with self.assertRaises(VerificationError):
            package_repository_artifacts(self.repository, bundle_path)

        self.assertEqual(bundle_path.read_bytes(), b"existing bundle")
        self.assertEqual(list(bundle_path.parent.glob(f".{bundle_path.name}.*.tmp")), [])

    def test_snapshot_rejects_file_replaced_between_lstat_and_open(self) -> None:
        source = self.repository / "snapshot-source.txt"
        replacement = self.repository / "snapshot-replacement.txt"
        source.write_bytes(b"original")
        replacement.write_bytes(b"replacement")
        real_open = os.open
        raced = False

        def replace_before_open(path: object, flags: int, mode: int = 0o777) -> int:
            nonlocal raced
            if Path(path) == source and not raced:
                raced = True
                os.replace(replacement, source)
            return real_open(path, flags, mode)

        with mock.patch("os.open", side_effect=replace_before_open):
            with self.assertRaisesRegex(VerificationError, "identity changed"):
                _snapshot_file(source, "raced snapshot")

    def test_snapshot_rejects_descriptor_identity_change_after_read(self) -> None:
        source = self.repository / "snapshot-source.txt"
        replacement = self.repository / "snapshot-replacement.txt"
        source.write_bytes(b"original")
        replacement.write_bytes(b"replacement")
        replacement_metadata = replacement.stat()
        real_fstat = os.fstat
        calls = 0

        def change_second_identity(descriptor: int) -> os.stat_result:
            nonlocal calls
            calls += 1
            if calls == 2:
                return replacement_metadata
            return real_fstat(descriptor)

        with mock.patch("os.fstat", side_effect=change_second_identity):
            with self.assertRaisesRegex(VerificationError, "identity changed"):
                _snapshot_file(source, "raced snapshot")

    def test_snapshot_rejects_descriptor_type_change_after_read(self) -> None:
        source = self.repository / "snapshot-source.txt"
        directory = self.repository / "replacement-directory"
        source.write_bytes(b"original")
        directory.mkdir()
        directory_metadata = directory.stat()
        real_fstat = os.fstat
        calls = 0

        def change_second_type(descriptor: int) -> os.stat_result:
            nonlocal calls
            calls += 1
            if calls == 2:
                return directory_metadata
            return real_fstat(descriptor)

        with mock.patch("os.fstat", side_effect=change_second_type):
            with self.assertRaisesRegex(VerificationError, "type changed"):
                _snapshot_file(source, "raced snapshot")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    def test_snapshot_open_uses_no_follow_when_available(self) -> None:
        source = self.repository / "snapshot-source.txt"
        source.write_bytes(b"snapshot")
        real_open = os.open
        observed_flags: list[int] = []

        def capture_flags(path: object, flags: int, mode: int = 0o777) -> int:
            observed_flags.append(flags)
            return real_open(path, flags, mode)

        with mock.patch("os.open", side_effect=capture_flags):
            self.assertEqual(_snapshot_file(source, "snapshot"), b"snapshot")

        self.assertEqual(len(observed_flags), 1)
        self.assertTrue(observed_flags[0] & os.O_NOFOLLOW)

    def test_cli_appends_bundle_digest_to_github_output(self) -> None:
        bundle_path = self.repository / "artifacts" / "proof.zip"
        github_output = self.repository / "github-output.txt"
        github_output.write_text("existing=value\n", encoding="utf-8", newline="\n")
        stdout = io.StringIO()

        with mock.patch("sys.stdout", new=stdout):
            result = main(
                [
                    "--repository-root",
                    str(self.repository),
                    "--bundle-path",
                    str(bundle_path),
                    "--github-output-path",
                    str(github_output),
                ]
            )

        digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        self.assertEqual(result, 0)
        self.assertEqual(
            github_output.read_text(encoding="utf-8").splitlines(),
            ["existing=value", f"bundle_sha256={digest}"],
        )
        self.assertIn(f"BUNDLE_SHA256={digest}", stdout.getvalue())

    def test_manifest_digest_tampering_fails(self) -> None:
        manifest_path = (
            self.repository
            / "governed-intelligence-sample"
            / "build"
            / "evaluation"
            / "output_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["decisions_jsonl"]["sha256"] = "0" * 64
        self._write_json(manifest_path, manifest)

        with self.assertRaisesRegex(VerificationError, "SHA-256 mismatch"):
            verify_repository_artifacts(self.repository)

    def test_rehashed_receipt_tampering_fails_semantic_verification(self) -> None:
        output_dir = (
            self.repository
            / "governed-intelligence-sample"
            / "build"
            / "evaluation"
        )
        receipts_path = output_dir / "decisions.jsonl"
        records = [
            json.loads(line)
            for line in receipts_path.read_text(encoding="utf-8").splitlines()
        ]
        records[0]["decision"]["disposition"] = "REFUSE"
        receipts_path.write_text(
            "".join(
                json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
                for record in records
            ),
            encoding="utf-8",
            newline="\n",
        )

        manifest_path = output_dir / "output_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["decisions_jsonl"]["sha256"] = hashlib.sha256(
            receipts_path.read_bytes()
        ).hexdigest()
        self._write_json(manifest_path, manifest)

        with self.assertRaisesRegex(VerificationError, "receipt verification failed"):
            verify_repository_artifacts(self.repository)

    def test_rehashed_qrels_with_stale_retrieval_metrics_fails(self) -> None:
        intelligence = self.repository / "governed-intelligence-sample"
        qrels_path = intelligence / "fixtures" / "retrieval_qrels.json"
        qrels = json.loads(qrels_path.read_text(encoding="utf-8"))
        qrels["judgments"][0]["relevant_record_ids"] = [
            qrels["corpus_binding"]["record_ids"][0]
        ]
        self._write_json(qrels_path, qrels)
        qrels_sha = hashlib.sha256(qrels_path.read_bytes()).hexdigest()

        output_dir = intelligence / "build" / "retrieval"
        report_path = output_dir / "retrieval_evaluation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["input_binding"]["retrieval_qrels_sha256"] = qrels_sha
        self._write_json(report_path, report)

        manifest_path = output_dir / "retrieval_output_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["input_binding"]["retrieval_qrels_sha256"] = qrels_sha
        self._write_json(manifest_path, manifest)
        self._rehash_manifest_output(
            output_dir,
            "retrieval_output_manifest.json",
            "retrieval_evaluation_report",
            report_path,
        )

        with self.assertRaisesRegex(
            VerificationError,
            "retrieved_relevant_count does not match verified receipts",
        ):
            verify_repository_artifacts(self.repository)

    def test_rehashed_grounding_report_with_stale_claim_totals_fails(self) -> None:
        output_dir = (
            self.repository
            / "governed-intelligence-sample"
            / "build"
            / "grounding"
        )
        report_path = output_dir / "grounding_evaluation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["checks"]["claim_pass_count"] = 4
        report["checks"]["claim_fail_count"] = 3
        self._write_json(report_path, report)
        self._rehash_manifest_output(
            output_dir,
            "grounding_output_manifest.json",
            "grounding_evaluation_report",
            report_path,
        )

        with self.assertRaisesRegex(
            VerificationError,
            "claim_pass_count does not match verified receipts",
        ):
            verify_repository_artifacts(self.repository)

    def test_rehashed_grounding_report_with_stale_dispositions_fails(self) -> None:
        output_dir = (
            self.repository
            / "governed-intelligence-sample"
            / "build"
            / "grounding"
        )
        report_path = output_dir / "grounding_evaluation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["disposition_counts"]["ADMIT"] = 2
        report["disposition_counts"]["QUARANTINE"] = 4
        self._write_json(report_path, report)
        self._rehash_manifest_output(
            output_dir,
            "grounding_output_manifest.json",
            "grounding_evaluation_report",
            report_path,
        )

        with self.assertRaisesRegex(
            VerificationError,
            "disposition counts do not match verified receipts",
        ):
            verify_repository_artifacts(self.repository)


if __name__ == "__main__":
    unittest.main()
