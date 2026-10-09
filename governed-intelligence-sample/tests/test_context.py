from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from decimal import InvalidOperation, ROUND_UP, localcontext
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

import hydra_governed_intelligence.context as context_module
from hydra_governed_intelligence import (
    ContractError,
    IntegrityError,
    build_decision,
    load_evidence,
    load_policy,
    verify_decision,
)
from hydra_governed_intelligence.context import (
    _is_link_or_reparse,
    _snapshot_regular_file,
)

from tests.support import ROOT, build_pipeline_outputs, build_pipeline_outputs_from_rows


class GovernedContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.pipeline_dir = build_pipeline_outputs(Path(self.temp_dir.name) / "pipeline")
        self.evidence = load_evidence(self.pipeline_dir)
        self.policy = load_policy(ROOT / "config/policy.json")

    def _new_pipeline_case(self, name: str) -> Path:
        return build_pipeline_outputs(Path(self.temp_dir.name) / name)

    def _rewrite_manifest(
        self, directory: Path, mutate: Callable[[dict[str, Any]], None]
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mutate(manifest)
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _object_digest(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def _rewrite_accepted_artifacts(
        self,
        directory: Path,
        mutate: Callable[[list[dict[str, Any]]], None],
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonl_descriptor = manifest["outputs"]["normalized_events_jsonl"]
        jsonl_path = directory / jsonl_descriptor["file"]
        records = [
            json.loads(line)
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        ]
        mutate(records)

        jsonl_bytes = b"".join(
            json.dumps(
                record,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
            for record in records
        )
        jsonl_path.write_bytes(jsonl_bytes)
        jsonl_descriptor["sha256"] = hashlib.sha256(jsonl_bytes).hexdigest()

        csv_descriptor = manifest["outputs"]["normalized_events_csv"]
        csv_path = directory / csv_descriptor["file"]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=csv_descriptor["schema"],
            lineterminator="\n",
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {column: record[column] for column in csv_descriptor["schema"]}
            )
        csv_bytes = buffer.getvalue().encode("utf-8")
        csv_path.write_bytes(csv_bytes)
        csv_descriptor["sha256"] = hashlib.sha256(csv_bytes).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def _rewrite_input_snapshot(
        self,
        directory: Path,
        input_key: str,
        raw: bytes,
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        descriptor = manifest["inputs"][input_key]
        (directory / descriptor["file"]).write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        descriptor["sha256"] = digest
        if input_key == "source_csv":
            manifest["source_file_sha256"] = digest
        else:
            manifest["aliases_sha256"] = digest
        manifest["pipeline_run_id"] = self._object_digest(
            {
                "aliases_sha256": manifest["aliases_sha256"],
                "run_schema": "hydra-market-pipeline-run/v1",
                "source_file_sha256": manifest["source_file_sha256"],
                "transform_version": manifest["transform_version"],
            }
        )
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def _rewrite_jsonl(
        self,
        directory: Path,
        output_key: str,
        mutate: Callable[[list[dict[str, Any]]], None],
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_path = directory / manifest["outputs"][output_key]["file"]
        records = [
            json.loads(line)
            for line in artifact_path.read_text(encoding="utf-8").splitlines()
        ]
        mutate(records)
        artifact_bytes = b"".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
            for record in records
        )
        artifact_path.write_bytes(artifact_bytes)
        manifest["outputs"][output_key]["sha256"] = hashlib.sha256(
            artifact_bytes
        ).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def _rewrite_artifact_bytes(
        self, directory: Path, output_key: str, artifact_bytes: bytes
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_path = directory / manifest["outputs"][output_key]["file"]
        artifact_path.write_bytes(artifact_bytes)
        manifest["outputs"][output_key]["sha256"] = hashlib.sha256(
            artifact_bytes
        ).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def _rename_manifest_output(
        self, directory: Path, output_key: str, filename: str
    ) -> None:
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        descriptor = manifest["outputs"][output_key]
        (directory / descriptor["file"]).rename(directory / filename)
        descriptor["file"] = filename
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def test_admitted_observation_has_exact_resolvable_citation(self) -> None:
        decision = build_decision(
            {
                "request_id": "test-aaa",
                "task_type": "accepted_observation_summary",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        verify_decision(decision, evidence=self.evidence, policy=self.policy)
        self.assertEqual(decision["disposition"], "ADMIT")
        self.assertEqual(len(decision["context"]["records"]), 1)
        self.assertEqual(decision["citations"][0]["artifact"], "normalized_events.jsonl")
        self.assertEqual(
            decision["model_execution"],
            {"authorized": False, "status": "NOT_EXECUTED"},
        )

    def test_quality_status_exposes_counts_but_not_quarantined_rows(self) -> None:
        decision = build_decision(
            {"request_id": "test-quality", "task_type": "quality_status", "subject": None},
            evidence=self.evidence,
            policy=self.policy,
        )

        verify_decision(decision, evidence=self.evidence, policy=self.policy)
        serialized = json.dumps(decision, sort_keys=True)
        self.assertEqual(decision["context"]["quarantined_rows"], 4)
        self.assertFalse(decision["context"]["quarantine_detail_included"])
        self.assertNotIn('"raw_record"', serialized)
        self.assertNotIn("quarantine_records.jsonl", serialized)

    def test_missing_evidence_abstains_and_trading_action_refuses(self) -> None:
        missing = build_decision(
            {
                "request_id": "test-missing",
                "task_type": "accepted_observation_summary",
                "subject": "ZZZ",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        trading = build_decision(
            {
                "request_id": "test-action",
                "task_type": "trading_instruction",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        self.assertEqual(
            (missing["disposition"], missing["reason_codes"]),
            ("ABSTAIN", ["no_governed_evidence"]),
        )
        self.assertEqual(
            (trading["disposition"], trading["reason_codes"]),
            ("REFUSE", ["action_not_authorized"]),
        )
        for decision in (missing, trading):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)
            self.assertIsNone(decision["context"])
            self.assertEqual(decision["citations"], [])

    def test_tampered_pipeline_output_fails_closed(self) -> None:
        normalized = self.pipeline_dir / "normalized_events.jsonl"
        normalized.write_bytes(normalized.read_bytes() + b"{}\n")

        with self.assertRaisesRegex(IntegrityError, "digest mismatch"):
            load_evidence(self.pipeline_dir)

    def test_load_evidence_rejects_symlinked_root_ancestor(self) -> None:
        linked_root = Path(self.temp_dir.name) / "pipeline-link"
        try:
            linked_root.symlink_to(self.pipeline_dir, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")

        with self.assertRaises(IntegrityError):
            load_evidence(linked_root)

    def test_reparse_file_attribute_is_detected(self) -> None:
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        metadata = SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_file_attributes=reparse_flag,
        )
        with patch.object(
            stat,
            "FILE_ATTRIBUTE_REPARSE_POINT",
            reparse_flag,
            create=True,
        ):
            self.assertTrue(_is_link_or_reparse(metadata))

    @unittest.skipUnless(os.name == "nt", "Windows handle APIs only")
    def test_snapshot_rejects_mocked_root_and_leaf_reparse_points(self) -> None:
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        for target_call in (1, 2):
            with self.subTest(target="root" if target_call == 1 else "leaf"):
                root = Path(self.temp_dir.name) / f"snapshot-reparse-{target_call}"
                root.mkdir()
                source = root / "source.txt"
                source.write_bytes(b"snapshot")
                real_information = context_module._windows_handle_information
                calls = 0

                def marked_information(handle: int) -> tuple[int, int, int]:
                    nonlocal calls
                    calls += 1
                    attributes, volume, identity = real_information(handle)
                    if calls == target_call:
                        attributes |= reparse_flag
                    return attributes, volume, identity

                with patch.object(
                    context_module,
                    "_windows_handle_information",
                    side_effect=marked_information,
                ):
                    with self.assertRaisesRegex(IntegrityError, "reparse point"):
                        _snapshot_regular_file(source, root, "reparse evidence")

    @unittest.skipUnless(os.name == "nt", "Windows handle APIs only")
    def test_snapshot_accepts_normal_windows_root(self) -> None:
        root = Path(self.temp_dir.name) / "snapshot-normal-root"
        root.mkdir()
        source = root / "source.txt"
        source.write_bytes(b"snapshot")
        self.assertEqual(
            _snapshot_regular_file(source, root, "normal Windows evidence"),
            b"snapshot",
        )

    def test_snapshot_rejects_mocked_ancestor_aba_redirect(self) -> None:
        root = Path(self.temp_dir.name) / "snapshot-aba"
        outside = Path(self.temp_dir.name) / "snapshot-outside"
        root.mkdir()
        outside.mkdir()
        source = root / "source.txt"
        alternate = outside / "source.txt"
        source.write_bytes(b"expected")
        alternate.write_bytes(b"external")

        if os.name == "nt":
            with patch.object(
                context_module,
                "_windows_open_relative_leaf",
                side_effect=lambda _root_handle, _name: context_module._windows_open_handle(
                    alternate,
                    directory=False,
                ),
            ):
                with self.assertRaisesRegex(IntegrityError, "physically contained"):
                    _snapshot_regular_file(source, root, "ABA evidence")
            return

        real_open = os.open

        def redirected_open(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            if (
                path == source.name
                and dir_fd is not None
                and not flags & os.O_DIRECTORY
            ):
                return real_open(alternate, flags, mode)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with patch("os.open", side_effect=redirected_open):
            with self.assertRaisesRegex(IntegrityError, "identity changed while opening"):
                _snapshot_regular_file(source, root, "ABA evidence")

    def test_snapshot_rejects_descriptor_identity_drift_after_read(self) -> None:
        root = Path(self.temp_dir.name) / "snapshot-identity"
        root.mkdir()
        source = root / "source.txt"
        replacement = root / "replacement.txt"
        source.write_bytes(b"original")
        replacement.write_bytes(b"replacement")
        replacement_metadata = replacement.stat()
        real_fstat = os.fstat
        regular_calls = 0
        changed_call = 2 if os.name == "nt" else 3

        def change_second_identity(descriptor: int) -> os.stat_result:
            nonlocal regular_calls
            actual = real_fstat(descriptor)
            if stat.S_ISREG(actual.st_mode):
                regular_calls += 1
            if regular_calls == changed_call:
                return replacement_metadata
            return actual

        with patch("os.fstat", side_effect=change_second_identity):
            with self.assertRaisesRegex(IntegrityError, "identity changed while reading"):
                _snapshot_regular_file(source, root, "raced evidence")

    @unittest.skipIf(os.name == "nt", "Windows uses relative NT handle opens")
    def test_snapshot_open_uses_no_follow_when_available(self) -> None:
        root = Path(self.temp_dir.name) / "snapshot-no-follow"
        root.mkdir()
        source = root / "source.txt"
        source.write_bytes(b"snapshot")
        real_open = os.open
        observed: list[tuple[object, int, int | None]] = []

        def capture_flags(
            path: object,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            observed.append((path, flags, dir_fd))
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with patch("os.open", side_effect=capture_flags):
            self.assertEqual(
                _snapshot_regular_file(source, root, "snapshot evidence"),
                b"snapshot",
            )

        leaf_opens = [
            (flags, dir_fd)
            for path, flags, dir_fd in observed
            if path == source.name and not flags & os.O_DIRECTORY
        ]
        self.assertEqual(len(leaf_opens), 1)
        self.assertTrue(leaf_opens[0][0] & os.O_NOFOLLOW)
        self.assertIsNotNone(leaf_opens[0][1])

    def test_manifest_v1_is_rejected_as_non_replayable(self) -> None:
        directory = self._new_pipeline_case("manifest-v1")

        def downgrade(manifest: dict[str, Any]) -> None:
            manifest["schema_version"] = "hydra-market-pipeline-manifest/v1"
            manifest.pop("inputs")
            manifest.pop("source_rows")

        self._rewrite_manifest(directory, downgrade)

        with self.assertRaisesRegex(ContractError, "v1 is non-replayable"):
            load_evidence(directory)

    def test_digest_consistent_forged_accepted_raw_hash_fails_replay(self) -> None:
        directory = self._new_pipeline_case("forged-accepted-raw-hash")
        self._rewrite_accepted_artifacts(
            directory,
            lambda records: records[0].__setitem__(
                "raw_record_sha256", "0" * 64
            ),
        )

        with self.assertRaisesRegex(IntegrityError, "independent pipeline replay"):
            load_evidence(directory)

    def test_digest_consistent_forged_quarantine_reason_fails_replay(self) -> None:
        directory = self._new_pipeline_case("forged-quarantine-reason")

        def forge_reason(records: list[dict[str, Any]]) -> None:
            record = records[0]
            record["errors"] = ["price_invalid"]
            record["validation_messages"] = ["price must be a decimal value"]
            record["quarantine_id"] = self._object_digest(
                {
                    "errors": record["errors"],
                    "raw_record_sha256": record["raw_record_sha256"],
                    "source_row_number": record["source_row_number"],
                }
            )

        self._rewrite_jsonl(
            directory,
            "quarantine_records_jsonl",
            forge_reason,
        )

        with self.assertRaisesRegex(IntegrityError, "independent pipeline replay"):
            load_evidence(directory)

    def test_digest_consistent_source_snapshot_tampering_fails_replay(self) -> None:
        directory = self._new_pipeline_case("tampered-source-snapshot")
        manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        source_path = directory / manifest["inputs"]["source_csv"]["file"]
        tampered = source_path.read_bytes().replace(b",-1.00,25,", b",1.00,25,", 1)
        self.assertNotEqual(tampered, source_path.read_bytes())
        self._rewrite_input_snapshot(directory, "source_csv", tampered)
        new_source_digest = hashlib.sha256(tampered).hexdigest()
        self._rewrite_accepted_artifacts(
            directory,
            lambda records: [
                record.__setitem__("source_file_sha256", new_source_digest)
                for record in records
            ],
        )

        with self.assertRaisesRegex(IntegrityError, "independent replay"):
            load_evidence(directory)

    def test_digest_consistent_alias_snapshot_tampering_fails_replay(self) -> None:
        directory = self._new_pipeline_case("tampered-alias-snapshot")
        manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        aliases_path = (
            directory / manifest["inputs"]["resolved_aliases_json"]["file"]
        )
        aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
        aliases["AAA.US"] = "ZZZ"
        alias_bytes = json.dumps(
            aliases,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._rewrite_input_snapshot(
            directory,
            "resolved_aliases_json",
            alias_bytes,
        )

        with self.assertRaisesRegex(IntegrityError, "independent replay"):
            load_evidence(directory)

    def test_replay_matches_alias_dependent_and_duplicate_outcomes(self) -> None:
        rows = [
            {
                "source_system": "SYNTH_A",
                "source_record_id": "alias-first",
                "symbol": "AAA.US",
                "event_time": "2026-09-24T17:30:00Z",
                "price": "10.00",
                "volume": "1",
                "currency": "usd",
                "venue": "XNAS",
            },
            {
                "source_system": "SYNTH_B",
                "source_record_id": "alias-duplicate",
                "symbol": "AAA",
                "event_time": "2026-09-24T17:30:00Z",
                "price": "10.00",
                "volume": "2",
                "currency": "USD",
                "venue": "XNAS",
            },
            {
                "source_system": "SYNTH_A",
                "source_record_id": "alias-special-key",
                "symbol": "BAD/SYM",
                "event_time": "2026-09-24T17:31:00Z",
                "price": "11.00",
                "volume": "3",
                "currency": "USD",
                "venue": "XNYS",
            },
            {
                "source_system": "SYNTH_A",
                "source_record_id": "invalid-first",
                "symbol": "CCC",
                "event_time": "2026-09-24T17:32:00Z",
                "price": "-1.00",
                "volume": "4",
                "currency": "USD",
                "venue": "XNAS",
            },
            {
                "source_system": "SYNTH_A",
                "source_record_id": "valid-after-invalid",
                "symbol": "CCC",
                "event_time": "2026-09-24T17:32:00Z",
                "price": "12.00",
                "volume": "5",
                "currency": "USD",
                "venue": "XNAS",
            },
        ]
        directory = build_pipeline_outputs_from_rows(
            Path(self.temp_dir.name) / "alias-duplicates",
            rows=rows,
            aliases={
                "AAA": "AAA",
                "AAA.US": "AAA",
                "BAD/SYM": "BBB",
                "CCC": "CCC",
            },
        )

        evidence = load_evidence(directory)
        quarantined = [
            json.loads(line)
            for line in (directory / "quarantine_records.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]

        self.assertEqual(evidence.manifest["source_rows"], 5)
        self.assertEqual(evidence.manifest["accepted_rows"], 3)
        self.assertEqual(evidence.manifest["quarantined_rows"], 2)
        self.assertEqual(
            {record["source_row_number"] for record in evidence.accepted_events},
            {2, 4, 6},
        )
        self.assertEqual(
            [(record["source_row_number"], record["errors"]) for record in quarantined],
            [
                (3, ["duplicate_normalized_event"]),
                (5, ["price_non_positive"]),
            ],
        )

    def test_replay_and_producer_ignore_ambient_decimal_context(self) -> None:
        baseline = self._new_pipeline_case("decimal-baseline")
        hostile = Path(self.temp_dir.name) / "decimal-hostile"

        with localcontext() as ambient:
            ambient.prec = 2
            ambient.rounding = ROUND_UP
            ambient.traps[InvalidOperation] = False
            build_pipeline_outputs(hostile)
            evidence = load_evidence(hostile)

        manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
        artifact_names = [
            manifest["inputs"]["source_csv"]["file"],
            manifest["inputs"]["resolved_aliases_json"]["file"],
            *(
                descriptor["file"]
                for descriptor in manifest["outputs"].values()
            ),
        ]
        for filename in artifact_names:
            with self.subTest(artifact=filename):
                self.assertEqual(
                    (hostile / filename).read_bytes(),
                    (baseline / filename).read_bytes(),
                )
        self.assertEqual(evidence.manifest["accepted_rows"], 3)
        self.assertEqual(evidence.manifest["quarantined_rows"], 4)

    def test_digest_consistent_numeric_currency_is_rejected_during_load(self) -> None:
        normalized = self.pipeline_dir / "normalized_events.jsonl"
        records = [
            json.loads(line)
            for line in normalized.read_text(encoding="utf-8").splitlines()
        ]
        records[0]["currency"] = 123
        normalized_bytes = b"".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
            for record in records
        )
        normalized.write_bytes(normalized_bytes)

        manifest_path = self.pipeline_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["normalized_events_jsonl"]["sha256"] = hashlib.sha256(
            normalized_bytes
        ).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            ContractError, "normalized event currency must be a string"
        ):
            load_evidence(self.pipeline_dir)

    def test_manifest_requires_exact_schema_types_and_bindings(self) -> None:
        def set_value(path: tuple[str, ...], value: Any) -> Callable[[dict[str, Any]], None]:
            def mutate(manifest: dict[str, Any]) -> None:
                target: dict[str, Any] = manifest
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value

            return mutate

        def remove_value(path: tuple[str, ...]) -> Callable[[dict[str, Any]], None]:
            def mutate(manifest: dict[str, Any]) -> None:
                target: dict[str, Any] = manifest
                for key in path[:-1]:
                    target = target[key]
                target.pop(path[-1])

            return mutate

        cases = (
            ("extra-top-level", set_value(("unexpected",), "value")),
            ("missing-top-level", remove_value(("aliases_sha256",))),
            ("accepted-float", set_value(("accepted_rows",), 3.0)),
            ("accepted-bool", set_value(("accepted_rows",), True)),
            ("quarantined-float", set_value(("quarantined_rows",), 4.0)),
            ("quarantined-bool", set_value(("quarantined_rows",), False)),
            ("source-rows-float", set_value(("source_rows",), 7.0)),
            ("source-rows-bool", set_value(("source_rows",), True)),
            ("source-rows-count", set_value(("source_rows",), 8)),
            ("negative-count", set_value(("accepted_rows",), -1)),
            ("run-id-type", set_value(("pipeline_run_id",), 7)),
            ("run-id-format", set_value(("pipeline_run_id",), "not-a-digest")),
            ("run-id-binding", set_value(("pipeline_run_id",), "0" * 64)),
            ("aliases-digest", set_value(("aliases_sha256",), "A" * 64)),
            ("source-digest", set_value(("source_file_sha256",), "bad")),
            ("transform-version", set_value(("transform_version",), "v2")),
            (
                "descriptor-extra-size",
                set_value(("outputs", "normalized_events_jsonl", "size"), 1),
            ),
            (
                "descriptor-extra-rows",
                set_value(("outputs", "quarantine_records_jsonl", "rows"), 4),
            ),
            (
                "descriptor-missing-digest",
                remove_value(("outputs", "normalized_events_jsonl", "sha256")),
            ),
            (
                "descriptor-file-type",
                set_value(("outputs", "normalized_events_jsonl", "file"), 1),
            ),
            (
                "descriptor-file-name",
                set_value(
                    ("outputs", "normalized_events_jsonl", "file"),
                    "other.jsonl",
                ),
            ),
            (
                "descriptor-digest-type",
                set_value(("outputs", "normalized_events_jsonl", "sha256"), 1),
            ),
            (
                "descriptor-digest-format",
                set_value(
                    ("outputs", "normalized_events_jsonl", "sha256"),
                    "not-a-digest",
                ),
            ),
            (
                "csv-schema-type",
                set_value(("outputs", "normalized_events_csv", "schema"), "event_id"),
            ),
            (
                "csv-schema-order",
                lambda manifest: manifest["outputs"]["normalized_events_csv"][
                    "schema"
                ].reverse(),
            ),
            ("missing-inputs", remove_value(("inputs",))),
            (
                "missing-source-input",
                remove_value(("inputs", "source_csv")),
            ),
            (
                "input-extra-field",
                set_value(("inputs", "source_csv", "size"), 1),
            ),
            (
                "input-file-name",
                set_value(("inputs", "source_csv", "file"), "other.csv"),
            ),
            (
                "input-schema",
                set_value(
                    ("inputs", "source_csv", "schema_version"),
                    "hydra-market-source-csv/v2",
                ),
            ),
            (
                "input-digest-format",
                set_value(("inputs", "source_csv", "sha256"), "bad"),
            ),
            (
                "input-source-digest-binding",
                set_value(("inputs", "source_csv", "sha256"), "0" * 64),
            ),
            (
                "input-alias-digest-binding",
                set_value(
                    ("inputs", "resolved_aliases_json", "sha256"),
                    "0" * 64,
                ),
            ),
        )

        for name, mutate in cases:
            with self.subTest(case=name):
                directory = self._new_pipeline_case(f"manifest-{name}")
                self._rewrite_manifest(directory, mutate)
                with self.assertRaises((ContractError, IntegrityError)):
                    load_evidence(directory)

    def test_manifest_output_filenames_are_safe_and_unique(self) -> None:
        for name, filename in (
            ("parent", "../other.jsonl"),
            ("forward-slash", "nested/other.jsonl"),
            ("backslash", "nested\\other.jsonl"),
            ("leading-space", " normalized.jsonl"),
            ("trailing-space", "normalized.jsonl "),
            ("trailing-dot", "normalized.jsonl."),
            ("device-name", "CON.jsonl"),
            ("device-name-mixed-case", "lPt9.csv"),
            ("device-name-superscript", "COM\u00b9.jsonl"),
            ("control-character", "normalized\x1fevents.jsonl"),
            ("forbidden-character", "normalized:events.jsonl"),
        ):
            with self.subTest(case=name):
                directory = self._new_pipeline_case(f"filename-{name}")
                self._rewrite_manifest(
                    directory,
                    lambda manifest, filename=filename: manifest["outputs"][
                        "normalized_events_jsonl"
                    ].__setitem__("file", filename),
                )
                with self.assertRaisesRegex(ContractError, "file name"):
                    load_evidence(directory)

        directory = self._new_pipeline_case("filename-duplicate")
        self._rewrite_manifest(
            directory,
            lambda manifest: manifest["outputs"][
                "quarantine_records_jsonl"
            ].__setitem__(
                "file",
                manifest["outputs"]["normalized_events_jsonl"]["file"],
            ),
        )
        with self.assertRaisesRegex(ContractError, "file name"):
            load_evidence(directory)

        directory = self._new_pipeline_case("filename-casefold-duplicate")
        self._rewrite_manifest(
            directory,
            lambda manifest: manifest["outputs"][
                "quarantine_records_jsonl"
            ].__setitem__(
                "file",
                manifest["outputs"]["normalized_events_jsonl"]["file"].upper(),
            ),
        )
        with self.assertRaisesRegex(ContractError, "file name"):
            load_evidence(directory)

    def test_manifest_output_rejects_safe_declared_renames(self) -> None:
        directory = self._new_pipeline_case("filename-safe-rename")
        self._rename_manifest_output(
            directory,
            "normalized_events_jsonl",
            "accepted-proof.jsonl",
        )

        with self.assertRaisesRegex(ContractError, "file name"):
            load_evidence(directory)

    def test_manifest_counts_bind_to_exact_artifact_row_counts(self) -> None:
        for field, value in (("accepted_rows", 2), ("quarantined_rows", 3)):
            with self.subTest(field=field):
                directory = self._new_pipeline_case(f"count-binding-{field}")
                self._rewrite_manifest(
                    directory,
                    lambda manifest, field=field, value=value: manifest.__setitem__(
                        field, value
                    ),
                )
                with self.assertRaisesRegex(IntegrityError, "row count"):
                    load_evidence(directory)

    def test_source_rows_form_exact_contiguous_producer_partition(self) -> None:
        directory = self._new_pipeline_case("accepted-dropped-phantom-row")

        def replace_accepted_row(records: list[dict[str, Any]]) -> None:
            record = next(
                record for record in records if record["source_row_number"] == 4
            )
            record["source_row_number"] = 99

        self._rewrite_jsonl(
            directory,
            "normalized_events_jsonl",
            replace_accepted_row,
        )
        with self.assertRaisesRegex(IntegrityError, "exact producer partition"):
            load_evidence(directory)

        directory = self._new_pipeline_case("quarantine-dropped-phantom-row")

        def replace_quarantine_row(records: list[dict[str, Any]]) -> None:
            record = next(
                record for record in records if record["source_row_number"] == 8
            )
            record["source_row_number"] = 99
            identity = {
                "errors": record["errors"],
                "raw_record_sha256": record["raw_record_sha256"],
                "source_row_number": record["source_row_number"],
            }
            record["quarantine_id"] = hashlib.sha256(
                json.dumps(
                    identity,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        self._rewrite_jsonl(
            directory,
            "quarantine_records_jsonl",
            replace_quarantine_row,
        )
        with self.assertRaisesRegex(IntegrityError, "exact producer partition"):
            load_evidence(directory)

    def test_normalized_events_require_canonical_values_and_provenance(self) -> None:
        def replace_field(field: str, value: Any) -> Callable[[list[dict[str, Any]]], None]:
            return lambda records: records[0].__setitem__(field, value)

        cases = (
            ("source-system-empty", replace_field("source_system", "")),
            ("source-system-whitespace", replace_field("source_system", " SYNTH_A")),
            ("source-system-unknown", replace_field("source_system", "LIVE_FEED")),
            ("source-record-empty", replace_field("source_record_id", "")),
            ("source-record-whitespace", replace_field("source_record_id", "   ")),
            ("symbol-empty", replace_field("symbol", "")),
            ("symbol-malformed", replace_field("symbol", "bad symbol")),
            ("timestamp-empty", replace_field("event_time_utc", "")),
            (
                "timestamp-invalid-date",
                replace_field("event_time_utc", "2026-02-30T17:31:00.000000Z"),
            ),
            (
                "timestamp-noncanonical",
                replace_field("event_time_utc", "2026-09-24T17:31:00Z"),
            ),
            ("price-empty", replace_field("price", "")),
            ("price-nonfinite", replace_field("price", "NaN")),
            ("price-nonpositive", replace_field("price", "0.000000")),
            ("price-scale", replace_field("price", "1.0000000")),
            ("price-notation", replace_field("price", "1e0")),
            ("currency-empty", replace_field("currency", "")),
            ("currency-malformed", replace_field("currency", "usd")),
            ("venue-empty", replace_field("venue", "")),
            ("venue-malformed", replace_field("venue", "xnas")),
            ("event-id-binding", replace_field("event_id", "0" * 64)),
            ("raw-digest-empty", replace_field("raw_record_sha256", "")),
            ("source-digest-binding", replace_field("source_file_sha256", "0" * 64)),
            ("row-bool", replace_field("source_row_number", True)),
            ("row-float", replace_field("source_row_number", 4.0)),
            ("volume-bool", replace_field("volume", True)),
            ("volume-float", replace_field("volume", 1.0)),
            ("volume-negative", replace_field("volume", -1)),
            ("transform-empty", replace_field("transform_version", "")),
            ("transform-invalid", replace_field("transform_version", "v2")),
            ("extra-status", lambda records: records[0].__setitem__("status", "PASS")),
            ("missing-provenance", lambda records: records[0].pop("raw_record_sha256")),
        )

        for name, mutate in cases:
            with self.subTest(case=name):
                directory = self._new_pipeline_case(f"event-{name}")
                self._rewrite_jsonl(
                    directory,
                    "normalized_events_jsonl",
                    mutate,
                )
                with self.assertRaises((ContractError, IntegrityError)):
                    load_evidence(directory)

    def test_accepted_jsonl_is_bound_to_csv_and_source_rows(self) -> None:
        directory = self._new_pipeline_case("csv-binding")
        csv_path = directory / "normalized_events.csv"
        altered_csv = csv_path.read_bytes().replace(b"SYNTH_A", b"SYNTH_X", 1)
        self._rewrite_artifact_bytes(
            directory,
            "normalized_events_csv",
            altered_csv,
        )
        with self.assertRaisesRegex(IntegrityError, "CSV rows"):
            load_evidence(directory)

        directory = self._new_pipeline_case("accepted-row-binding")
        self._rewrite_jsonl(
            directory,
            "normalized_events_jsonl",
            lambda records: records[1].__setitem__(
                "source_row_number", records[0]["source_row_number"]
            ),
        )
        with self.assertRaisesRegex(IntegrityError, "source_row_number"):
            load_evidence(directory)

        directory = self._new_pipeline_case("canonical-jsonl-size")
        normalized = directory / "normalized_events.jsonl"
        self._rewrite_artifact_bytes(
            directory,
            "normalized_events_jsonl",
            normalized.read_bytes().replace(b'{"currency"', b'{ "currency"', 1),
        )
        with self.assertRaisesRegex(ContractError, "canonical JSONL"):
            load_evidence(directory)

    def test_quarantine_records_require_exact_internal_bindings(self) -> None:
        def change_raw_record(records: list[dict[str, Any]]) -> None:
            records[0]["raw_record"]["price"] = "999.00"

        cases = (
            ("raw-record-digest", change_raw_record),
            (
                "quarantine-id",
                lambda records: records[0].__setitem__("quarantine_id", "0" * 64),
            ),
            (
                "validation-message",
                lambda records: records[0].__setitem__(
                    "validation_messages", ["incorrect"]
                ),
            ),
            (
                "unknown-error",
                lambda records: records[0].__setitem__("errors", ["unknown"]),
            ),
            ("stage", lambda records: records[0].__setitem__("stage", "other")),
            ("row-bool", lambda records: records[0].__setitem__("source_row_number", True)),
            ("extra-field", lambda records: records[0].__setitem__("status", "FAIL")),
            ("missing-field", lambda records: records[0].pop("raw_record_sha256")),
        )

        for name, mutate in cases:
            with self.subTest(case=name):
                directory = self._new_pipeline_case(f"quarantine-{name}")
                self._rewrite_jsonl(
                    directory,
                    "quarantine_records_jsonl",
                    mutate,
                )
                with self.assertRaises((ContractError, IntegrityError)):
                    load_evidence(directory)

        def overlap_accepted_row(records: list[dict[str, Any]]) -> None:
            record = records[0]
            record["source_row_number"] = 2
            identity = {
                "errors": record["errors"],
                "raw_record_sha256": record["raw_record_sha256"],
                "source_row_number": record["source_row_number"],
            }
            record["quarantine_id"] = hashlib.sha256(
                json.dumps(
                    identity,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        directory = self._new_pipeline_case("quarantine-overlap")
        self._rewrite_jsonl(
            directory,
            "quarantine_records_jsonl",
            overlap_accepted_row,
        )
        with self.assertRaisesRegex(IntegrityError, "source rows overlap"):
            load_evidence(directory)

    def test_verified_evidence_graph_is_immutable(self) -> None:
        with self.assertRaises(TypeError):
            self.evidence.accepted_events[0]["symbol"] = "ZZZ"
        with self.assertRaises(TypeError):
            self.evidence.manifest["outputs"]["normalized_events_jsonl"][
                "file"
            ] = "forged.jsonl"

    def test_changed_evidence_cannot_retain_verified_digest_binding(self) -> None:
        event = dict(self.evidence.accepted_events[0])
        event["symbol"] = "ZZZ"
        forged_events = (
            MappingProxyType(event),
            *self.evidence.accepted_events[1:],
        )
        replaced = replace(self.evidence, accepted_events=forged_events)
        constructed = type(self.evidence)(
            directory=self.evidence.directory,
            manifest=self.evidence.manifest,
            manifest_sha256=self.evidence.manifest_sha256,
            accepted_events=forged_events,
            normalized_filename=self.evidence.normalized_filename,
            normalized_sha256=self.evidence.normalized_sha256,
            quarantine_sha256=self.evidence.quarantine_sha256,
            _manifest_bytes=self.evidence._manifest_bytes,
            _output_snapshots=self.evidence._output_snapshots,
            _input_snapshots=self.evidence._input_snapshots,
        )
        request = {
            "request_id": "test-forged-evidence",
            "task_type": "accepted_observation_summary",
            "subject": "ZZZ",
        }
        genuine_decision = build_decision(
            {
                "request_id": "test-genuine-evidence",
                "task_type": "accepted_observation_summary",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        for forged in (replaced, constructed):
            with self.subTest(construction=forged is constructed):
                with self.assertRaisesRegex(IntegrityError, "evidence semantic binding"):
                    build_decision(request, evidence=forged, policy=self.policy)
                with self.assertRaisesRegex(IntegrityError, "evidence semantic binding"):
                    verify_decision(
                        genuine_decision,
                        evidence=forged,
                        policy=self.policy,
                    )

    def test_changed_input_snapshot_cannot_retain_verified_binding(self) -> None:
        forged_snapshots = tuple(
            (
                key,
                raw + b"\n" if key == "resolved_aliases_json" else raw,
            )
            for key, raw in self.evidence._input_snapshots
        )
        forged = replace(self.evidence, _input_snapshots=forged_snapshots)

        with self.assertRaisesRegex(IntegrityError, "evidence semantic binding"):
            build_decision(
                {
                    "request_id": "test-forged-input-snapshot",
                    "task_type": "quality_status",
                    "subject": None,
                },
                evidence=forged,
                policy=self.policy,
            )

    def test_changed_policy_cannot_retain_verified_digest_binding(self) -> None:
        replaced = replace(
            self.policy,
            allowed_tasks=(*self.policy.allowed_tasks, "trading_instruction"),
            refused_tasks=(),
        )
        constructed = type(self.policy)(
            allowed_tasks=(*self.policy.allowed_tasks, "trading_instruction"),
            abstained_tasks=self.policy.abstained_tasks,
            refused_tasks=(),
            max_context_records=self.policy.max_context_records,
            sha256=self.policy.sha256,
            _source_bytes=self.policy._source_bytes,
        )
        request = {
            "request_id": "test-forged-policy",
            "task_type": "trading_instruction",
            "subject": "AAA",
        }
        genuine_decision = build_decision(
            {
                "request_id": "test-genuine-policy",
                "task_type": "quality_status",
                "subject": None,
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        for forged in (replaced, constructed):
            with self.subTest(construction=forged is constructed):
                with self.assertRaisesRegex(IntegrityError, "policy semantic binding"):
                    build_decision(request, evidence=self.evidence, policy=forged)
                with self.assertRaisesRegex(IntegrityError, "policy semantic binding"):
                    verify_decision(
                        genuine_decision,
                        evidence=self.evidence,
                        policy=forged,
                    )

    def test_context_request_fields_require_exact_builtin_strings(self) -> None:
        class DeceptiveString(str):
            def upper(self) -> str:
                return "AAA"

        requests = (
            {
                "request_id": DeceptiveString("test-request-id"),
                "task_type": "quality_status",
                "subject": None,
            },
            {
                "request_id": "test-task-type",
                "task_type": DeceptiveString("quality_status"),
                "subject": None,
            },
            {
                "request_id": "test-subject",
                "task_type": "accepted_observation_summary",
                "subject": DeceptiveString("ZZZ"),
            },
        )

        for request in requests:
            deceptive_field = next(
                key
                for key, value in request.items()
                if type(value) is DeceptiveString
            )
            with self.subTest(field=deceptive_field):
                with self.assertRaises(ContractError):
                    build_decision(
                        request,
                        evidence=self.evidence,
                        policy=self.policy,
                    )

    def test_noncanonical_decision_containers_are_rejected(self) -> None:
        decision = build_decision(
            {
                "request_id": "test-tuple-output",
                "task_type": "accepted_observation_summary",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["reason_codes"] = tuple(decision["reason_codes"])

        with self.assertRaisesRegex(IntegrityError, "noncanonical JSON"):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)

        decision = build_decision(
            {
                "request_id": "test-mapping-output",
                "task_type": "quality_status",
                "subject": None,
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["context"] = MappingProxyType(decision["context"])

        with self.assertRaisesRegex(IntegrityError, "noncanonical JSON"):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)

    def test_nonfinite_decision_float_is_rejected_as_integrity_error(self) -> None:
        decision = build_decision(
            {
                "request_id": "test-nan-output",
                "task_type": "accepted_observation_summary",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["context"]["records"][0]["price"] = float("nan")

        with self.assertRaisesRegex(IntegrityError, "non-finite float"):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)

    def test_tampered_citation_is_rejected(self) -> None:
        decision = build_decision(
            {
                "request_id": "test-citation",
                "task_type": "accepted_observation_summary",
                "subject": "BBB",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["citations"][0]["record_sha256"] = "0" * 64

        with self.assertRaisesRegex(IntegrityError, "citation is invalid"):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)

    def test_tampered_admitted_context_is_rejected(self) -> None:
        observation = build_decision(
            {
                "request_id": "test-context",
                "task_type": "accepted_observation_summary",
                "subject": "BBB",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        observation["context"]["records"][0]["price"] = "999999.000000"
        quality = build_decision(
            {
                "request_id": "test-quality-context",
                "task_type": "quality_status",
                "subject": None,
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        quality["context"]["accepted_rows"] = 999

        with self.assertRaisesRegex(IntegrityError, "observation context is invalid"):
            verify_decision(observation, evidence=self.evidence, policy=self.policy)
        with self.assertRaisesRegex(IntegrityError, "quality context is invalid"):
            verify_decision(quality, evidence=self.evidence, policy=self.policy)

    def test_authorization_rewrite_and_extra_fields_are_rejected(self) -> None:
        decision = build_decision(
            {
                "request_id": "test-rewrite",
                "task_type": "accepted_observation_summary",
                "subject": "AAA",
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["task_type"] = "trading_instruction"
        decision["request_id"] = "rewritten"
        decision["reason_codes"] = ["action_not_authorized"]
        decision["extra"] = "payload"

        with self.assertRaisesRegex(IntegrityError, "governed recomputation"):
            verify_decision(decision, evidence=self.evidence, policy=self.policy)

    def test_evidence_parses_the_exact_digest_checked_bytes(self) -> None:
        artifact_cases = (
            ("manifest", lambda root, manifest: root / "manifest.json"),
            (
                "source-input",
                lambda root, manifest: root
                / manifest["inputs"]["source_csv"]["file"],
            ),
            (
                "aliases-input",
                lambda root, manifest: root
                / manifest["inputs"]["resolved_aliases_json"]["file"],
            ),
            (
                "normalized-csv",
                lambda root, manifest: root
                / manifest["outputs"]["normalized_events_csv"]["file"],
            ),
            (
                "normalized-jsonl",
                lambda root, manifest: root
                / manifest["outputs"]["normalized_events_jsonl"]["file"],
            ),
            (
                "quarantine-jsonl",
                lambda root, manifest: root
                / manifest["outputs"]["quarantine_records_jsonl"]["file"],
            ),
        )
        original_snapshot = _snapshot_regular_file

        for name, locate in artifact_cases:
            with self.subTest(artifact=name):
                directory = self._new_pipeline_case(f"exact-bytes-{name}")
                manifest = json.loads(
                    (directory / "manifest.json").read_text(encoding="utf-8")
                )
                target = locate(directory, manifest)
                swapped = False

                def snapshot_and_swap(path: Path, root: Path, label: str) -> bytes:
                    nonlocal swapped
                    raw = original_snapshot(path, root, label)
                    if path == target and not swapped:
                        swapped = True
                        path.write_bytes(raw + b"\n")
                    return raw

                with patch.object(
                    context_module,
                    "_snapshot_regular_file",
                    side_effect=snapshot_and_swap,
                ):
                    evidence = load_evidence(directory)

                self.assertTrue(swapped)
                self.assertEqual(evidence.manifest["accepted_rows"], 3)
                self.assertEqual(evidence.manifest["quarantined_rows"], 4)

    def test_policy_cannot_enable_model_execution(self) -> None:
        policy_path = Path(self.temp_dir.name) / "unsafe-policy.json"
        policy = json.loads((ROOT / "config/policy.json").read_text(encoding="utf-8"))
        policy["model_execution_enabled"] = True
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "prohibits model execution"):
            load_policy(policy_path)


class PipelineReplayHeaderCompatibilityTests(unittest.TestCase):
    def _assert_header_variant_replays(self, *, padded: bool) -> None:
        from tests.support import PIPELINE, run_pipeline, write_outputs

        source = (PIPELINE / "data/raw/synthetic_market_events.csv").read_bytes()
        header, body = source.split(b"\n", 1)
        candidate_header = (
            b",".join(b" " + field + b" " for field in header.split(b","))
            if padded
            else header
        )
        candidate = candidate_header + b"\n" + body
        self.assertEqual(candidate.split(b"\n", 1)[1], body)
        self.assertEqual(candidate_header != header, padded)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "source.csv"
            source_path.write_bytes(candidate)
            result = run_pipeline(
                input_csv=source_path,
                aliases_path=PIPELINE / "config/symbol_aliases.json",
            )
            self.assertEqual(result.transform_version, "hydra-market-normalizer/v2")
            self.assertEqual(result.source_csv_bytes, candidate)
            self.assertEqual(result.source_file_sha256, hashlib.sha256(candidate).hexdigest())
            self.assertEqual(sorted(event.symbol for event in result.accepted), ["AAA", "BBB", "EEE"])
            self.assertEqual(
                {record.source_row_number: tuple(record.errors) for record in result.quarantined},
                {
                    3: ("duplicate_normalized_event",),
                    5: ("event_time_invalid",),
                    6: ("price_non_positive",),
                    8: ("source_system_invalid",),
                },
            )
            expected_aliases = json.loads(
                (PIPELINE / "config/symbol_aliases.json").read_text(encoding="utf-8")
            )
            alias_bytes = json.dumps(
                expected_aliases, allow_nan=False, ensure_ascii=False,
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
            self.assertEqual(dict(result.resolved_aliases), expected_aliases)
            self.assertEqual(result.aliases_sha256, hashlib.sha256(alias_bytes).hexdigest())
            run_identity = {
                "aliases_sha256": result.aliases_sha256,
                "run_schema": "hydra-market-pipeline-run/v1",
                "source_file_sha256": result.source_file_sha256,
                "transform_version": "hydra-market-normalizer/v2",
            }
            run_bytes = json.dumps(
                run_identity, allow_nan=False, ensure_ascii=False,
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
            self.assertEqual(result.pipeline_run_id, hashlib.sha256(run_bytes).hexdigest())

            output_dir = root / "outputs"
            outputs = write_outputs(result, output_dir=output_dir)
            self.assertEqual(outputs["source_snapshot"].read_bytes(), candidate)
            self.assertEqual(outputs["resolved_aliases_json"].read_bytes(), alias_bytes)
            manifest_bytes = outputs["manifest"].read_bytes()
            manifest = json.loads(manifest_bytes)
            self.assertEqual(manifest["accepted_rows"], 3)
            self.assertEqual(manifest["quarantined_rows"], 4)
            self.assertEqual(manifest["source_rows"], 7)
            self.assertEqual(manifest["pipeline_run_id"], result.pipeline_run_id)
            for key in ("aliases_sha256", "source_file_sha256", "transform_version"):
                self.assertEqual(manifest[key], run_identity[key])

            evidence = load_evidence(output_dir)
            self.assertEqual(evidence.manifest_sha256, hashlib.sha256(manifest_bytes).hexdigest())
            self.assertEqual(evidence.manifest["pipeline_run_id"], result.pipeline_run_id)
            self.assertEqual(evidence.manifest["transform_version"], "hydra-market-normalizer/v2")
            self.assertEqual(
                [dict(event) for event in evidence.accepted_events],
                [event.json_record() for event in result.accepted],
            )
            self.assertEqual(
                dict(evidence._input_snapshots),
                {"source_csv": candidate, "resolved_aliases_json": alias_bytes},
            )
            for key, snapshot in evidence._output_snapshots:
                self.assertEqual(snapshot, (output_dir / manifest["outputs"][key]["file"]).read_bytes())
                self.assertEqual(hashlib.sha256(snapshot).hexdigest(), manifest["outputs"][key]["sha256"])

    def test_unpadded_v2_artifacts_pass_independent_replay(self) -> None:
        self._assert_header_variant_replays(padded=False)

    def test_padded_v2_artifacts_pass_independent_replay(self) -> None:
        self._assert_header_variant_replays(padded=True)


if __name__ == "__main__":
    unittest.main()
