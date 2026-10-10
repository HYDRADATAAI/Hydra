from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import secrets
import shutil
import subprocess
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
    BundleSummary,
    ZIP_EXTERNAL_ATTR,
    ZIP_TIMESTAMP,
    VerificationError,
    _build_bundle_bytes,
    _open_bound_leaf,
    _publish_bundle,
    _snapshot_file,
    _snapshot_repository_file,
    _snapshot_verification_inputs,
    _verify_bundle,
    _windows_open_path,
    _windows_open_relative,
    main,
    package_repository_artifacts,
    verify_repository_artifacts,
)

from tests.support import ROOT, build_pipeline_outputs


class PreUploadVerifierStaticContractTests(unittest.TestCase):
    def test_manifest_v2_bundle_member_contract(self) -> None:
        self.assertEqual(len(BUNDLE_MEMBERS), 15)
        self.assertIn(
            "market-data-pipeline-sample/build/demo/source_snapshot.csv",
            BUNDLE_MEMBERS,
        )
        self.assertIn(
            "market-data-pipeline-sample/build/demo/resolved_symbol_aliases.json",
            BUNDLE_MEMBERS,
        )

    def test_manifest_v2_summary_contract(self) -> None:
        summary = BundleSummary(
            manifest_outputs=9,
            receipts=26,
            input_snapshots_verified=2,
            source_rows_replayed=7,
            bundle_members=15,
            bundle_bytes=1,
            bundle_sha256="0" * 64,
        )

        self.assertEqual(summary.input_snapshots_verified, 2)
        self.assertEqual(summary.source_rows_replayed, 7)


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

        qrels_path = intelligence / "fixtures" / "retrieval_qrels.json"
        qrels = json.loads(qrels_path.read_text(encoding="utf-8"))
        qrels["corpus_binding"]["pipeline_manifest_sha256"] = hashlib.sha256(
            (pipeline / "manifest.json").read_bytes()
        ).hexdigest()
        qrels_path.write_text(
            json.dumps(qrels, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

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
        (self.repository / "artifacts").mkdir()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    @staticmethod
    def _create_directory_link(link: Path, target: Path) -> None:
        if os.name == "nt":
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise OSError(detail or "unable to create directory junction")
            return
        link.symlink_to(target, target_is_directory=True)

    @staticmethod
    def _remove_directory_link(link: Path) -> None:
        if not os.path.lexists(link):
            return
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()

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
        self.assertEqual(summary.input_snapshots_verified, 2)
        self.assertEqual(summary.source_rows_replayed, 7)

    def test_deterministic_bundle_is_byte_identical(self) -> None:
        first_path = self.repository / "artifacts" / "first.zip"
        second_path = self.repository / "artifacts" / "second.zip"

        first = package_repository_artifacts(self.repository, first_path)
        second = package_repository_artifacts(self.repository, second_path)
        first_bytes = first_path.read_bytes()
        second_bytes = second_path.read_bytes()

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first.bundle_members, 15)
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
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_bytes(b"existing bundle")
        (self.repository / Path(BUNDLE_MEMBERS[0])).unlink()

        with self.assertRaises(VerificationError):
            package_repository_artifacts(self.repository, bundle_path)

        self.assertEqual(bundle_path.read_bytes(), b"existing bundle")
        self.assertEqual(list(bundle_path.parent.glob(f".{bundle_path.name}.*.tmp")), [])

    def test_successful_replacement_overwrites_existing_bundle(self) -> None:
        bundle_path = self.repository / "artifacts" / "proof.zip"

        _publish_bundle(bundle_path, b"first bundle")
        _publish_bundle(bundle_path, b"replacement bundle")

        self.assertEqual(bundle_path.read_bytes(), b"replacement bundle")
        self.assertEqual(list(bundle_path.parent.glob(f".{bundle_path.name}.*.tmp")), [])

    def test_failed_atomic_rename_removes_temporary_bundle(self) -> None:
        bundle_path = self.repository / "artifacts" / "proof.zip"
        target = (
            "hydra_governed_intelligence.pre_upload_verifier._windows_replace_relative"
            if os.name == "nt"
            else "hydra_governed_intelligence.pre_upload_verifier.os.replace"
        )

        with mock.patch(target, side_effect=OSError("injected rename failure")):
            with self.assertRaisesRegex(VerificationError, "unable to publish atomically"):
                _publish_bundle(bundle_path, b"bundle bytes")

        self.assertFalse(bundle_path.exists())
        self.assertEqual(list(bundle_path.parent.glob(f".{bundle_path.name}.*.tmp")), [])

    def test_publish_bundle_rejects_linked_ancestor_without_external_artifact(self) -> None:
        linked_parent = self.repository / "artifacts"
        external_parent = Path(self.temp_dir.name) / "external-artifacts"
        external_parent.mkdir()
        linked_parent.rmdir()
        bundle_path = linked_parent / "proof.zip"
        external_bundle = external_parent / bundle_path.name
        failure: VerificationError | None = None

        try:
            self._create_directory_link(linked_parent, external_parent)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlink or junction creation unavailable: {exc}")

        try:
            try:
                _publish_bundle(bundle_path, b"bundle bytes")
            except VerificationError as exc:
                failure = exc
        finally:
            self._remove_directory_link(linked_parent)

        self.assertFalse(
            external_bundle.exists(),
            "bundle publication followed a linked ancestor into an external directory",
        )
        self.assertIsNotNone(failure, "linked publication ancestor must fail closed")

    def test_linked_ancestor_cannot_create_external_parent(self) -> None:
        linked_parent = self.repository / "redirected-artifacts"
        external_parent = Path(self.temp_dir.name) / "external-parent"
        external_parent.mkdir()
        bundle_path = linked_parent / "missing" / "proof.zip"

        try:
            self._create_directory_link(linked_parent, external_parent)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlink or junction creation unavailable: {exc}")

        try:
            with self.assertRaises(VerificationError):
                _publish_bundle(bundle_path, b"bundle bytes")
        finally:
            self._remove_directory_link(linked_parent)

        self.assertFalse(external_parent.joinpath("missing").exists())

    def test_ancestor_swap_during_temporary_creation_cannot_redirect_bundle(self) -> None:
        bound_parent = self.repository / "artifacts"
        saved_parent = self.repository / "artifacts-original"
        replacement_parent = Path(self.temp_dir.name) / "replacement-artifacts"
        replacement_parent.mkdir()
        bundle_path = bound_parent / "proof.zip"
        payload = b"bundle bytes"
        attempted = False
        swapped = False
        failure: VerificationError | None = None

        def swap_ancestor() -> None:
            nonlocal attempted, swapped
            attempted = True
            bound_parent.rename(saved_parent)
            try:
                replacement_parent.rename(bound_parent)
            except OSError:
                saved_parent.rename(bound_parent)
                raise
            swapped = True

        real_token_hex = secrets.token_hex
        real_named_temporary_file = tempfile.NamedTemporaryFile

        def swap_ancestor_then_name(nbytes: int | None = None) -> str:
            if not attempted:
                swap_ancestor()
            return real_token_hex(nbytes)

        def swap_ancestor_then_create_legacy(
            *args: object,
            **kwargs: object,
        ) -> object:
            if not attempted:
                swap_ancestor()
            return real_named_temporary_file(*args, **kwargs)

        patchers = (
            mock.patch("secrets.token_hex", side_effect=swap_ancestor_then_name),
            mock.patch(
                "hydra_governed_intelligence.pre_upload_verifier.tempfile.NamedTemporaryFile",
                side_effect=swap_ancestor_then_create_legacy,
            ),
        )

        try:
            with contextlib.ExitStack() as stack:
                for patcher in patchers:
                    stack.enter_context(patcher)
                try:
                    _publish_bundle(bundle_path, payload)
                except VerificationError as exc:
                    failure = exc
        finally:
            if swapped:
                bound_parent.rename(replacement_parent)
                saved_parent.rename(bound_parent)

        self.assertTrue(attempted)
        self.assertFalse(
            (replacement_parent / bundle_path.name).exists(),
            "bundle publication was redirected into the replacement directory",
        )
        if failure is None:
            self.assertEqual(bundle_path.read_bytes(), payload)

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

    def test_snapshot_rejects_final_reparse_point(self) -> None:
        source = self.repository / "snapshot-source.txt"
        source.write_bytes(b"snapshot")
        metadata = source.lstat()
        reparse_metadata = mock.Mock(
            st_mode=metadata.st_mode,
            st_file_attributes=0x400,
        )

        with mock.patch.object(Path, "lstat", return_value=reparse_metadata):
            with self.assertRaisesRegex(
                VerificationError,
                "symbolic links and reparse points are not allowed",
            ):
                _snapshot_file(source, "snapshot")

    def test_snapshot_rejects_symlinked_ancestor(self) -> None:
        ancestor = self.repository / "governed-intelligence-sample"
        target = self.repository / "governed-intelligence-target"
        ancestor.rename(target)
        try:
            ancestor.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            if os.path.lexists(ancestor):
                ancestor.unlink()
            target.rename(ancestor)
            self.skipTest(f"directory symlink creation unavailable: {exc}")

        with self.assertRaisesRegex(
            VerificationError,
            r"symbolic(?: links and reparse points|[-]link or reparse-point ancestors) are not allowed",
        ):
            _snapshot_verification_inputs(self.repository)

    def test_snapshot_rejects_symlinked_repository_root(self) -> None:
        linked_root = Path(self.temp_dir.name) / "repository-link"
        try:
            linked_root.symlink_to(self.repository, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            if os.path.lexists(linked_root):
                linked_root.unlink()
            self.skipTest(f"directory symlink creation unavailable: {exc}")

        with self.assertRaisesRegex(
            VerificationError,
            "repository root must not be a symbolic link or reparse point",
        ):
            _snapshot_verification_inputs(linked_root)

    def test_ancestor_swap_during_leaf_open_cannot_redirect_snapshot(self) -> None:
        root = self.repository.absolute()
        ancestor = root / "governed-intelligence-sample" / "config"
        saved_ancestor = ancestor.with_name("config-original")
        replacement = ancestor.with_name("config-replacement")
        shutil.copytree(ancestor, replacement)
        candidate = ancestor / "policy.json"
        expected = candidate.read_bytes()
        (replacement / candidate.name).write_bytes(b"redirected outside snapshot")
        real_open_bound_leaf = _open_bound_leaf
        attempted = False
        swapped = False

        def swap_ancestor_then_open(
            parent_handle: int,
            leaf_name: str,
            opened_candidate: Path,
            label: str,
        ) -> int:
            nonlocal attempted, swapped
            attempted = True
            try:
                ancestor.rename(saved_ancestor)
                try:
                    replacement.rename(ancestor)
                    swapped = True
                except OSError:
                    saved_ancestor.rename(ancestor)
            except OSError:
                pass
            return real_open_bound_leaf(
                parent_handle,
                leaf_name,
                opened_candidate,
                label,
            )

        try:
            with mock.patch(
                "hydra_governed_intelligence.pre_upload_verifier._open_bound_leaf",
                side_effect=swap_ancestor_then_open,
            ):
                try:
                    snapshot = _snapshot_repository_file(
                        root,
                        candidate,
                        "swap snapshot",
                    )
                except VerificationError as exc:
                    self.assertRegex(
                        str(exc),
                        "opened handle physical path changed|identity changed",
                    )
                else:
                    self.assertEqual(snapshot, expected)
        finally:
            if swapped:
                ancestor.rename(replacement)
                saved_ancestor.rename(ancestor)

        self.assertTrue(attempted)
        if not swapped:
            self.skipTest("ancestor swap unavailable on this filesystem")
        self.assertNotEqual(
            (replacement / candidate.name).read_bytes(),
            expected,
        )

    @unittest.skipUnless(os.name == "nt", "Windows handle semantics only")
    def test_windows_mocked_leaf_aba_external_file_fails(self) -> None:
        root = self.repository.absolute()
        candidate = root / "governed-intelligence-sample" / "config" / "policy.json"
        external = Path(self.temp_dir.name) / "external-policy.json"
        external.write_bytes(b"external policy bytes")
        real_open_relative = _windows_open_relative

        def redirect_leaf_after_path_restored(
            parent_handle: int,
            name: str,
            label: str,
            *,
            directory: bool,
        ) -> int:
            if not directory and name == candidate.name:
                return _windows_open_path(external, label, directory=False)
            return real_open_relative(
                parent_handle,
                name,
                label,
                directory=directory,
            )

        with mock.patch(
            "hydra_governed_intelligence.pre_upload_verifier._windows_open_relative",
            side_effect=redirect_leaf_after_path_restored,
        ):
            with self.assertRaisesRegex(
                VerificationError,
                "opened handle physical path changed",
            ):
                _snapshot_repository_file(root, candidate, "Windows leaf ABA")

    @unittest.skipUnless(os.name == "nt", "Windows handle semantics only")
    def test_windows_root_aba_external_handle_fails(self) -> None:
        root = self.repository.absolute()
        candidate = root / "governed-intelligence-sample" / "config" / "policy.json"
        external_root = Path(self.temp_dir.name) / "external-root"
        external_root.mkdir()
        real_open_path = _windows_open_path

        def redirect_root_after_lstat(
            path: Path,
            label: str,
            *,
            directory: bool,
        ) -> int:
            if directory and Path(path) == root:
                return real_open_path(external_root, label, directory=True)
            return real_open_path(path, label, directory=directory)

        with mock.patch(
            "hydra_governed_intelligence.pre_upload_verifier._windows_open_path",
            side_effect=redirect_root_after_lstat,
        ):
            with self.assertRaisesRegex(
                VerificationError,
                "repository root identity changed|opened handle physical path changed",
            ):
                _snapshot_repository_file(root, candidate, "Windows root ABA")

    def test_snapshot_rejects_candidate_outside_repository_root(self) -> None:
        outside = Path(self.temp_dir.name) / "outside.txt"
        outside.write_bytes(b"outside repository")

        with self.assertRaisesRegex(
            VerificationError,
            "path is not contained under the repository root",
        ):
            _snapshot_repository_file(
                self.repository.resolve(strict=True),
                outside,
                "outside snapshot",
            )

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
            [
                "existing=value",
                f"bundle_sha256={digest}",
                "input_snapshots_verified=2",
                "source_rows_replayed=7",
            ],
        )
        self.assertIn(f"BUNDLE_SHA256={digest}", stdout.getvalue())
        self.assertIn("INPUT_SNAPSHOTS_VERIFIED=2", stdout.getvalue())
        self.assertIn("SOURCE_ROWS_REPLAYED=7", stdout.getvalue())

    def test_input_snapshot_digest_tampering_fails(self) -> None:
        snapshot_path = (
            self.repository
            / "market-data-pipeline-sample"
            / "build"
            / "demo"
            / "source_snapshot.csv"
        )
        snapshot_path.write_bytes(snapshot_path.read_bytes() + b"tampered\n")

        with self.assertRaisesRegex(VerificationError, "SHA-256 mismatch"):
            verify_repository_artifacts(self.repository)

    def test_manifest_v1_fails_closed(self) -> None:
        manifest_path = (
            self.repository
            / "market-data-pipeline-sample"
            / "build"
            / "demo"
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["schema_version"] = "hydra-market-pipeline-manifest/v1"
        self._write_json(manifest_path, manifest)

        with self.assertRaisesRegex(VerificationError, "schema changed"):
            verify_repository_artifacts(self.repository)

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
