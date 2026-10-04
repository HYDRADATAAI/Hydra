from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable
from unittest.mock import patch

from hydra_governed_intelligence import (
    ContractError,
    IntegrityError,
    build_decision,
    load_evidence,
    load_policy,
    verify_decision,
)

from tests.support import ROOT, build_pipeline_outputs


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
        ):
            with self.subTest(case=name):
                directory = self._new_pipeline_case(f"filename-{name}")
                self._rewrite_manifest(
                    directory,
                    lambda manifest, filename=filename: manifest["outputs"][
                        "normalized_events_jsonl"
                    ].__setitem__("file", filename),
                )
                with self.assertRaisesRegex(ContractError, "unsafe file name"):
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
        with self.assertRaisesRegex(ContractError, "unsafe file name"):
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
        normalized = self.pipeline_dir / "normalized_events.jsonl"
        original_read_bytes = Path.read_bytes
        swapped = False

        def read_and_swap(path: Path) -> bytes:
            nonlocal swapped
            raw = original_read_bytes(path)
            if path == normalized and not swapped:
                swapped = True
                forged = raw.replace(b'"symbol":"AAA"', b'"symbol":"ZZZ"', 1)
                path.write_bytes(forged)
            return raw

        with patch.object(Path, "read_bytes", read_and_swap):
            evidence = load_evidence(self.pipeline_dir)

        self.assertTrue(swapped)
        self.assertIn("AAA", {event["symbol"] for event in evidence.accepted_events})
        self.assertNotIn("ZZZ", {event["symbol"] for event in evidence.accepted_events})

    def test_policy_cannot_enable_model_execution(self) -> None:
        policy_path = Path(self.temp_dir.name) / "unsafe-policy.json"
        policy = json.loads((ROOT / "config/policy.json").read_text(encoding="utf-8"))
        policy["model_execution_enabled"] = True
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "prohibits model execution"):
            load_policy(policy_path)


if __name__ == "__main__":
    unittest.main()
