from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_governed_intelligence import load_evidence, load_policy, run_evaluation

from tests.support import ROOT, build_pipeline_outputs


class GovernedEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.evidence = load_evidence(build_pipeline_outputs(self.base / "pipeline"))
        self.policy = load_policy(ROOT / "config/policy.json")

    def test_evaluation_passes_all_control_cases(self) -> None:
        report = run_evaluation(
            cases_path=ROOT / "fixtures/evaluation_cases.json",
            evidence=self.evidence,
            policy=self.policy,
            output_dir=self.base / "evaluation",
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(
            report["disposition_counts"],
            {"ABSTAIN": 2, "ADMIT": 2, "REFUSE": 1},
        )
        self.assertEqual(report["checks"]["disposition_match_count"], 5)
        self.assertEqual(report["checks"]["citation_integrity_pass_count"], 5)
        self.assertEqual(report["checks"]["unauthorized_model_execution_count"], 0)
        self.assertEqual(report["checks"]["quarantined_raw_records_exposed_count"], 0)

    def test_evaluation_outputs_are_byte_deterministic(self) -> None:
        outputs = []
        for name in ("first", "second"):
            output_dir = self.base / name
            run_evaluation(
                cases_path=ROOT / "fixtures/evaluation_cases.json",
                evidence=self.evidence,
                policy=self.policy,
                output_dir=output_dir,
            )
            outputs.append(output_dir)

        for filename in ("decisions.jsonl", "evaluation_report.json", "output_manifest.json"):
            self.assertEqual(
                (outputs[0] / filename).read_bytes(),
                (outputs[1] / filename).read_bytes(),
            )

    def test_expectation_drift_produces_failing_receipt(self) -> None:
        suite = json.loads(
            (ROOT / "fixtures/evaluation_cases.json").read_text(encoding="utf-8")
        )
        suite["cases"][0]["expected"]["disposition"] = "ABSTAIN"
        changed_suite = self.base / "changed-suite.json"
        changed_suite.write_text(json.dumps(suite), encoding="utf-8")

        report = run_evaluation(
            cases_path=changed_suite,
            evidence=self.evidence,
            policy=self.policy,
            output_dir=self.base / "failed-evaluation",
        )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["disposition_match_count"], 4)
        self.assertEqual(
            report["failures"][0]["case_id"],
            "accepted-observation-has-resolvable-citation",
        )


if __name__ == "__main__":
    unittest.main()
