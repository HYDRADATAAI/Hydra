from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_governed_intelligence import (
    load_evidence,
    load_retrieval_policy,
    run_retrieval_evaluation,
)

from tests.support import ROOT, build_pipeline_outputs


class GovernedRetrievalEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.evidence = load_evidence(build_pipeline_outputs(self.base / "pipeline"))
        self.policy = load_retrieval_policy(ROOT / "config/retrieval_policy.json")

    def test_benchmark_passes_all_cases_and_metrics(self) -> None:
        report = run_retrieval_evaluation(
            cases_path=ROOT / "fixtures/retrieval_cases.json",
            evidence=self.evidence,
            policy=self.policy,
            output_dir=self.base / "retrieval",
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 6)
        self.assertEqual(
            report["disposition_counts"],
            {"ABSTAIN": 2, "ADMIT": 3, "REFUSE": 1},
        )
        self.assertEqual(report["checks"]["expectation_match_count"], 6)
        self.assertEqual(report["checks"]["citation_integrity_pass_count"], 6)
        self.assertEqual(report["checks"]["retrieval_case_count"], 3)
        self.assertEqual(report["checks"]["recall_at_k"], "1.000000")
        self.assertEqual(report["checks"]["mean_reciprocal_rank"], "1.000000")
        self.assertEqual(report["checks"]["unauthorized_model_execution_count"], 0)
        self.assertEqual(report["checks"]["quarantined_raw_records_exposed_count"], 0)

    def test_benchmark_outputs_are_byte_deterministic(self) -> None:
        outputs = []
        for name in ("first", "second"):
            output_dir = self.base / name
            run_retrieval_evaluation(
                cases_path=ROOT / "fixtures/retrieval_cases.json",
                evidence=self.evidence,
                policy=self.policy,
                output_dir=output_dir,
            )
            outputs.append(output_dir)

        for filename in (
            "retrieval_decisions.jsonl",
            "retrieval_evaluation_report.json",
            "retrieval_output_manifest.json",
        ):
            self.assertEqual(
                (outputs[0] / filename).read_bytes(),
                (outputs[1] / filename).read_bytes(),
            )

    def test_expectation_drift_produces_failing_receipt(self) -> None:
        suite = json.loads(
            (ROOT / "fixtures/retrieval_cases.json").read_text(encoding="utf-8")
        )
        suite["cases"][0]["expected"]["ranked_symbols"] = ["BBB"]
        changed_suite = self.base / "changed-retrieval-suite.json"
        changed_suite.write_text(json.dumps(suite), encoding="utf-8")

        report = run_retrieval_evaluation(
            cases_path=changed_suite,
            evidence=self.evidence,
            policy=self.policy,
            output_dir=self.base / "failed-retrieval",
        )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["expectation_match_count"], 5)
        self.assertEqual(report["failures"][0]["case_id"], "accepted-aaa-ranks-first")


if __name__ == "__main__":
    unittest.main()
