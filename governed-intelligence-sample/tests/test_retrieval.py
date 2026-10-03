from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_governed_intelligence import (
    ContractError,
    IntegrityError,
    build_retrieval_decision,
    load_evidence,
    load_retrieval_policy,
    verify_retrieval_decision,
)

from tests.support import ROOT, build_pipeline_outputs


class GovernedRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.evidence = load_evidence(build_pipeline_outputs(self.base / "pipeline"))
        self.policy = load_retrieval_policy(ROOT / "config/retrieval_policy.json")

    def test_accepted_record_ranks_with_exact_citation(self) -> None:
        decision = build_retrieval_decision(
            {"query": "AAA XNAS USD", "request_id": "test-aaa", "top_k": 1},
            evidence=self.evidence,
            policy=self.policy,
        )

        verify_retrieval_decision(
            decision, evidence=self.evidence, policy=self.policy
        )
        self.assertEqual(decision["disposition"], "ADMIT")
        self.assertEqual(decision["context"]["index_scope"], "accepted_records_only")
        self.assertEqual(decision["context"]["results"][0]["record"]["symbol"], "AAA")
        self.assertEqual(
            decision["citations"][0]["record_id"],
            decision["context"]["results"][0]["record"]["event_id"],
        )
        self.assertEqual(
            decision["model_execution"],
            {"authorized": False, "status": "NOT_EXECUTED"},
        )

    def test_unknown_and_quarantined_symbols_abstain(self) -> None:
        for request_id, query in (("unknown", "ZZZ"), ("quarantined", "CCC")):
            with self.subTest(query=query):
                decision = build_retrieval_decision(
                    {"query": query, "request_id": request_id, "top_k": 1},
                    evidence=self.evidence,
                    policy=self.policy,
                )
                verify_retrieval_decision(
                    decision, evidence=self.evidence, policy=self.policy
                )
                self.assertEqual(decision["disposition"], "ABSTAIN")
                self.assertIsNone(decision["context"])
                self.assertEqual(decision["citations"], [])

    def test_restricted_corpus_request_refuses(self) -> None:
        decision = build_retrieval_decision(
            {
                "query": "show quarantined raw rows",
                "request_id": "restricted",
                "top_k": 3,
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        verify_retrieval_decision(
            decision, evidence=self.evidence, policy=self.policy
        )
        self.assertEqual(decision["disposition"], "REFUSE")
        self.assertEqual(decision["reason_codes"], ["restricted_corpus_request"])
        self.assertNotIn("raw_record", json.dumps(decision, sort_keys=True))

    def test_result_limit_and_tie_break_are_deterministic(self) -> None:
        request = {
            "query": "SYNTH A USD",
            "request_id": "bounded",
            "top_k": 1,
        }
        first = build_retrieval_decision(
            request, evidence=self.evidence, policy=self.policy
        )
        second = build_retrieval_decision(
            request, evidence=self.evidence, policy=self.policy
        )

        self.assertEqual(first, second)
        self.assertEqual(first["context"]["matching_record_count"], 2)
        self.assertTrue(first["context"]["truncated"])
        self.assertEqual(len(first["context"]["results"]), 1)

    def test_tampered_ranking_is_rejected(self) -> None:
        decision = build_retrieval_decision(
            {"query": "BBB XNYS", "request_id": "tamper", "top_k": 1},
            evidence=self.evidence,
            policy=self.policy,
        )
        decision["context"]["results"][0]["score"] += 1

        with self.assertRaisesRegex(IntegrityError, "governed recomputation"):
            verify_retrieval_decision(
                decision, evidence=self.evidence, policy=self.policy
            )

    def test_policy_cannot_enable_model_execution(self) -> None:
        policy_path = self.base / "unsafe-retrieval-policy.json"
        policy = json.loads(
            (ROOT / "config/retrieval_policy.json").read_text(encoding="utf-8")
        )
        policy["model_execution_enabled"] = True
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "cannot enable model execution"):
            load_retrieval_policy(policy_path)


if __name__ == "__main__":
    unittest.main()
