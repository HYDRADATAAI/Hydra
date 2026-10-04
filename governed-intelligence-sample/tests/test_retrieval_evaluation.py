from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hydra_governed_intelligence import (
    ContractError,
    load_evidence,
    load_retrieval_policy,
    run_retrieval_evaluation,
)
from hydra_governed_intelligence.retrieval_cli import build_parser
from hydra_governed_intelligence.context import load_json_document_with_bytes

from tests.support import ROOT, build_pipeline_outputs


class GovernedRetrievalEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.evidence = load_evidence(build_pipeline_outputs(self.base / "pipeline"))
        self.policy = load_retrieval_policy(ROOT / "config/retrieval_policy.json")
        self.cases_path = ROOT / "fixtures/retrieval_cases.json"
        self.qrels_path = ROOT / "fixtures/retrieval_qrels.json"

    def test_benchmark_passes_all_cases_and_independent_metrics(self) -> None:
        report = self._run(output_name="retrieval")

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 13)
        self.assertEqual(
            report["disposition_counts"],
            {"ABSTAIN": 6, "ADMIT": 4, "REFUSE": 3},
        )
        checks = report["checks"]
        self.assertEqual(checks["expectation_match_count"], 13)
        self.assertEqual(checks["decision_verification_pass_count"], 13)
        self.assertEqual(checks["quality_case_count"], 6)
        self.assertEqual(checks["qrel_case_count"], 6)
        self.assertEqual(checks["relevant_judgment_count"], 9)
        self.assertEqual(checks["retrieved_relevant_count"], 4)
        self.assertEqual(checks["recall_at_k"], "0.444444")
        self.assertEqual(checks["micro_recall_at_k"], "0.444444")
        self.assertEqual(checks["macro_recall_at_k"], "0.583333")
        self.assertEqual(checks["mean_reciprocal_rank"], "0.666667")
        self.assertEqual(checks["hard_negative_case_count"], 4)
        self.assertEqual(checks["hard_negative_false_admit_count"], 0)
        self.assertEqual(checks["citation_applicable_case_count"], 4)
        self.assertEqual(checks["citation_integrity_pass_case_count"], 4)
        self.assertEqual(checks["verified_citation_count"], 4)
        self.assertEqual(checks["citation_not_applicable_case_count"], 9)
        self.assertEqual(checks["unauthorized_model_execution_count"], 0)
        self.assertEqual(checks["quarantined_raw_records_exposed_count"], 0)
        self.assertEqual(
            report["input_binding"]["retrieval_qrels_sha256"],
            hashlib.sha256(self.qrels_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["input_binding"]["normalized_events_sha256"],
            self.evidence.normalized_sha256,
        )

    def test_benchmark_outputs_are_byte_deterministic(self) -> None:
        outputs = []
        for name in ("first", "second"):
            self._run(output_name=name)
            outputs.append(self.base / name)

        for filename in (
            "retrieval_decisions.jsonl",
            "retrieval_evaluation_report.json",
            "retrieval_output_manifest.json",
        ):
            self.assertEqual(
                (outputs[0] / filename).read_bytes(),
                (outputs[1] / filename).read_bytes(),
            )

    def test_report_hashes_the_exact_loaded_json_snapshots(self) -> None:
        snapshot_cases = self.base / "snapshot-cases.json"
        snapshot_qrels = self.base / "snapshot-qrels.json"
        suite_bytes = self.cases_path.read_bytes()
        qrels_bytes = self.qrels_path.read_bytes()
        snapshot_cases.write_bytes(suite_bytes)
        snapshot_qrels.write_bytes(qrels_bytes)

        def load_then_replace(path: Path) -> tuple[object, bytes]:
            document, raw = load_json_document_with_bytes(path)
            path.write_bytes(b"{}\n")
            return document, raw

        with patch(
            "hydra_governed_intelligence.retrieval_evaluation.load_json_document_with_bytes",
            side_effect=load_then_replace,
        ):
            report = self._run(
                output_name="snapshot-hashes",
                cases_path=snapshot_cases,
                qrels_path=snapshot_qrels,
            )

        self.assertEqual(
            report["input_binding"]["retrieval_suite_sha256"],
            hashlib.sha256(suite_bytes).hexdigest(),
        )
        self.assertEqual(
            report["input_binding"]["retrieval_qrels_sha256"],
            hashlib.sha256(qrels_bytes).hexdigest(),
        )

    def test_qrels_change_metrics_without_changing_behavior_expectations(self) -> None:
        qrels = self._read_json(self.qrels_path)
        eee_record_id = next(
            event["event_id"]
            for event in self.evidence.accepted_events
            if event["symbol"] == "EEE"
        )
        qrels["judgments"][0]["relevant_record_ids"] = [eee_record_id]
        changed_qrels = self._write_json("changed-qrels.json", qrels)

        report = self._run(output_name="changed-qrels", qrels_path=changed_qrels)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["expectation_match_count"], 13)
        self.assertEqual(report["checks"]["micro_recall_at_k"], "0.333333")
        self.assertEqual(report["checks"]["macro_recall_at_k"], "0.416667")
        self.assertEqual(report["checks"]["mean_reciprocal_rank"], "0.500000")

    def test_citation_case_and_record_counts_are_distinct(self) -> None:
        suite = self._read_json(self.cases_path)
        shared_case = next(
            case
            for case in suite["cases"]
            if case["case_id"] == "shared-source-bounded-recall"
        )
        shared_case["request"]["top_k"] = 2
        shared_case["expected"]["ranked_symbols"] = ["BBB", "AAA"]
        changed_cases = self._write_json("multi-citation-cases.json", suite)

        report = self._run(output_name="multi-citation", cases_path=changed_cases)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["citation_applicable_case_count"], 4)
        self.assertEqual(report["checks"]["citation_integrity_pass_case_count"], 4)
        self.assertEqual(report["checks"]["verified_citation_count"], 5)

    def test_expectation_drift_produces_failing_receipt(self) -> None:
        suite = self._read_json(self.cases_path)
        suite["cases"][0]["expected"]["ranked_symbols"] = ["BBB"]
        changed_suite = self._write_json("changed-retrieval-suite.json", suite)

        report = self._run(output_name="failed-retrieval", cases_path=changed_suite)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["expectation_match_count"], 12)
        self.assertEqual(report["failures"][0]["case_id"], "accepted-aaa-ranks-first")

    def test_malformed_qrels_fail_closed(self) -> None:
        qrels = self._read_json(self.qrels_path)
        qrels["judgments"][0]["unexpected"] = True
        malformed_qrels = self._write_json("malformed-qrels.json", qrels)

        with self.assertRaisesRegex(ContractError, "qrels judgment is invalid"):
            self._run(output_name="malformed", qrels_path=malformed_qrels)

    def test_unhashable_metric_group_fails_with_contract_error(self) -> None:
        suite = self._read_json(self.cases_path)
        suite["cases"][0]["metric_group"] = []
        malformed = self._write_json("malformed-case-suite.json", suite)

        with self.assertRaisesRegex(ContractError, "metric_group is invalid"):
            self._run(output_name="malformed-case", cases_path=malformed)

    def test_qrels_corpus_binding_rejects_drift(self) -> None:
        base_qrels = self._read_json(self.qrels_path)
        variants = []

        manifest_drift = json.loads(json.dumps(base_qrels))
        manifest_drift["corpus_binding"]["pipeline_manifest_sha256"] = "0" * 64
        variants.append(("manifest", manifest_drift, "pipeline manifest digest"))

        artifact_drift = json.loads(json.dumps(base_qrels))
        artifact_drift["corpus_binding"]["normalized_events_sha256"] = "0" * 64
        variants.append(("artifact", artifact_drift, "normalized artifact digest"))

        record_drift = json.loads(json.dumps(base_qrels))
        record_ids = record_drift["corpus_binding"]["record_ids"]
        record_drift["corpus_binding"]["record_ids"] = sorted(record_ids[1:] + ["f" * 64])
        variants.append(("records", record_drift, "record IDs do not match"))

        for name, qrels, message in variants:
            with self.subTest(name=name):
                path = self._write_json(f"{name}-drift-qrels.json", qrels)
                with self.assertRaisesRegex(ContractError, message):
                    self._run(output_name=f"{name}-drift", qrels_path=path)

    def test_qrels_case_ids_must_match_quality_cases(self) -> None:
        qrels = self._read_json(self.qrels_path)
        qrels["judgments"].pop()
        incomplete_qrels = self._write_json("incomplete-qrels.json", qrels)

        with self.assertRaisesRegex(ContractError, "case IDs do not match quality cases"):
            self._run(output_name="incomplete", qrels_path=incomplete_qrels)

    def test_relevant_record_ids_must_resolve_inside_bound_corpus(self) -> None:
        qrels = self._read_json(self.qrels_path)
        qrels["judgments"][0]["relevant_record_ids"] = ["f" * 64]
        invalid_qrels = self._write_json("invalid-record-qrels.json", qrels)

        with self.assertRaisesRegex(ContractError, "outside the bound corpus"):
            self._run(output_name="invalid-record", qrels_path=invalid_qrels)

    def test_cli_requires_and_parses_qrels_path(self) -> None:
        args = build_parser().parse_args(
            [
                "--pipeline-output-dir",
                "pipeline",
                "--policy",
                "policy.json",
                "--cases",
                "cases.json",
                "--qrels",
                "qrels.json",
                "--output-dir",
                "output",
            ]
        )

        self.assertEqual(args.qrels, Path("qrels.json"))

    def _run(
        self,
        *,
        output_name: str,
        cases_path: Path | None = None,
        qrels_path: Path | None = None,
    ) -> dict[str, object]:
        return run_retrieval_evaluation(
            cases_path=cases_path or self.cases_path,
            qrels_path=qrels_path or self.qrels_path,
            evidence=self.evidence,
            policy=self.policy,
            output_dir=self.base / output_name,
        )

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, filename: str, value: object) -> Path:
        path = self.base / filename
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
