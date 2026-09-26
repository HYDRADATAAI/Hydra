from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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

    def test_policy_cannot_enable_model_execution(self) -> None:
        policy_path = Path(self.temp_dir.name) / "unsafe-policy.json"
        policy = json.loads((ROOT / "config/policy.json").read_text(encoding="utf-8"))
        policy["model_execution_enabled"] = True
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "prohibits model execution"):
            load_policy(policy_path)


if __name__ == "__main__":
    unittest.main()
