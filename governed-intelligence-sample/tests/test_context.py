from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
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
