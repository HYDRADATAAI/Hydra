from __future__ import annotations

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from hydra_governed_intelligence import (
    ContractError,
    GroundingPolicy,
    IntegrityError,
    build_grounding_receipt,
    load_evidence,
    load_grounding_policy,
    load_retrieval_policy,
    run_grounding_evaluation,
    verify_grounding_receipt,
)

from tests.support import ROOT, build_pipeline_outputs


class GroundingValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.evidence = load_evidence(build_pipeline_outputs(self.base / "pipeline"))
        self.retrieval_policy = load_retrieval_policy(
            ROOT / "config/retrieval_policy.json"
        )
        self.grounding_policy = load_grounding_policy(
            ROOT / "config/grounding_policy.json"
        )
        self.suite = json.loads(
            (ROOT / "fixtures/grounding_cases.json").read_text(encoding="utf-8")
        )

    def receipt_for(self, index: int) -> dict:
        case = self.suite["cases"][index]
        return build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

    def nonempty_nonadmitted_case(self, index: int, label: str) -> dict:
        case = copy.deepcopy(self.suite["cases"][index])
        claim = copy.deepcopy(self.suite["cases"][0]["candidate"]["claims"][0])
        case["candidate"]["response_id"] = f"sensitive-{label}-response"
        claim["claim_id"] = f"sensitive-{label}-claim"
        case["candidate"]["claims"] = [claim]
        return case

    def test_valid_structured_claims_are_admitted_with_exact_citation(self) -> None:
        case = self.suite["cases"][0]
        receipt = self.receipt_for(0)

        verify_grounding_receipt(
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        self.assertEqual(receipt["disposition"], "ADMIT")
        self.assertEqual(len(receipt["grounded_claims"]), 2)
        self.assertEqual(len(receipt["citations"]), 1)
        self.assertEqual(
            receipt["model_execution"],
            {"authorized": False, "status": "NOT_EXECUTED"},
        )
        self.assertEqual(
            receipt["external_actions"],
            {"authorized": False, "status": "NOT_EXECUTED"},
        )
        self.assertEqual(
            receipt["input_binding"]["candidate"]["status"],
            "DISCLOSED_AND_BOUND",
        )
        self.assertRegex(
            receipt["input_binding"]["candidate"]["sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_grounding_defects_are_quarantined_without_claim_leakage(self) -> None:
        expected = {
            1: "claim_value_mismatch",
            2: "record_outside_retrieved_context",
            3: "citation_mismatch",
            4: "field_not_allowed",
        }
        for index, reason in expected.items():
            with self.subTest(reason=reason):
                receipt = self.receipt_for(index)
                self.assertEqual(receipt["disposition"], "QUARANTINE")
                self.assertIn(reason, receipt["reason_codes"])
                self.assertEqual(receipt["grounded_claims"], [])
                self.assertEqual(receipt["citations"], [])
                self.assertEqual(
                    receipt["input_binding"]["candidate"],
                    {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"},
                )

    def test_retrieval_abstain_and_refuse_propagate(self) -> None:
        abstain = self.receipt_for(5)
        refuse = self.receipt_for(6)

        self.assertEqual(
            (abstain["disposition"], abstain["reason_codes"]),
            ("ABSTAIN", ["retrieval_not_admitted"]),
        )
        self.assertEqual(
            (refuse["disposition"], refuse["reason_codes"]),
            ("REFUSE", ["retrieval_refused"]),
        )
        for receipt in (abstain, refuse):
            self.assertEqual(
                receipt["input_binding"]["candidate"],
                {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"},
            )

    def test_clean_nonempty_claim_is_not_evaluated_when_retrieval_abstains(self) -> None:
        case = self.nonempty_nonadmitted_case(5, "abstain")

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "ABSTAIN")
        self.assertEqual(receipt["reason_codes"], ["retrieval_not_admitted"])
        self.assertEqual(
            receipt["claim_results"],
            [
                {
                    "claim_index": 1,
                    "reason_codes": [],
                    "status": "NOT_EVALUATED",
                }
            ],
        )
        self.assertEqual(receipt["grounded_claims"], [])
        self.assertEqual(receipt["citations"], [])

    def test_clean_nonempty_claim_is_not_evaluated_when_retrieval_refuses(self) -> None:
        case = self.nonempty_nonadmitted_case(6, "refuse")

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "REFUSE")
        self.assertEqual(receipt["reason_codes"], ["retrieval_refused"])
        self.assertEqual(
            receipt["claim_results"],
            [
                {
                    "claim_index": 1,
                    "reason_codes": [],
                    "status": "NOT_EVALUATED",
                }
            ],
        )
        self.assertEqual(receipt["grounded_claims"], [])
        self.assertEqual(receipt["citations"], [])

    def test_execution_and_external_action_claims_are_quarantined(self) -> None:
        receipt = self.receipt_for(7)

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertEqual(
            receipt["reason_codes"],
            [
                "candidate_model_execution_claim_rejected",
                "external_actions_requested",
            ],
        )
        self.assertEqual(receipt["grounded_claims"], [])

    def test_unsafe_candidate_is_quarantined_when_retrieval_abstains(self) -> None:
        case = copy.deepcopy(self.suite["cases"][5])
        case["candidate"].update(
            {
                "external_actions_requested": True,
                "model_execution_status": "EXECUTED",
                "producer": "untrusted_producer",
                "request_id": "wrong-request",
            }
        )

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertEqual(
            receipt["reason_codes"],
            [
                "candidate_request_binding_mismatch",
                "candidate_producer_not_allowed",
                "candidate_model_execution_claim_rejected",
                "external_actions_requested",
                "retrieval_not_admitted",
            ],
        )

    def test_unsafe_candidate_is_quarantined_when_retrieval_refuses(self) -> None:
        case = copy.deepcopy(self.suite["cases"][6])
        case["candidate"]["model_execution_status"] = "EXECUTED"
        case["candidate"]["external_actions_requested"] = True

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertEqual(
            receipt["reason_codes"],
            [
                "candidate_model_execution_claim_rejected",
                "external_actions_requested",
                "retrieval_refused",
            ],
        )

    def test_disallowed_claim_field_is_quarantined_when_retrieval_abstains(self) -> None:
        case = copy.deepcopy(self.suite["cases"][5])
        case["candidate"]["claims"] = [
            copy.deepcopy(self.suite["cases"][4]["candidate"]["claims"][0])
        ]

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertEqual(
            receipt["reason_codes"],
            ["field_not_allowed", "retrieval_not_admitted"],
        )
        self.assertEqual(
            receipt["claim_results"],
            [
                {
                    "claim_index": 1,
                    "reason_codes": ["field_not_allowed"],
                    "status": "FAIL",
                }
            ],
        )
        self.assertEqual(receipt["grounded_claims"], [])
        self.assertEqual(receipt["citations"], [])
        self.assertIsNone(receipt["candidate_response_id"])
        self.assertEqual(
            receipt["input_binding"]["candidate"],
            {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"},
        )
        verify_grounding_receipt(
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

    def test_duplicate_claims_are_quarantined_when_retrieval_refuses(self) -> None:
        case = copy.deepcopy(self.suite["cases"][6])
        claim = copy.deepcopy(self.suite["cases"][0]["candidate"]["claims"][0])
        case["candidate"]["claims"] = [claim, copy.deepcopy(claim)]

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertEqual(
            receipt["reason_codes"],
            ["duplicate_claim_id", "retrieval_refused"],
        )
        self.assertEqual(receipt["claim_results"][0]["status"], "NOT_EVALUATED")
        self.assertEqual(
            receipt["claim_results"][1],
            {
                "claim_index": 2,
                "reason_codes": ["duplicate_claim_id"],
                "status": "FAIL",
            },
        )
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertEqual(receipt["grounded_claims"], [])
        self.assertEqual(receipt["citations"], [])
        self.assertIsNone(receipt["candidate_response_id"])
        self.assertNotIn(claim["claim_id"], serialized)
        self.assertNotIn(case["candidate"]["response_id"], serialized)
        self.assertNotIn("candidate_sha256", serialized)
        verify_grounding_receipt(
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

    def test_non_admitted_not_evaluated_status_tampering_is_rejected(self) -> None:
        case = self.nonempty_nonadmitted_case(5, "tamper")
        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        receipt["claim_results"][0]["status"] = "PASS"

        with self.assertRaisesRegex(IntegrityError, "governed recomputation"):
            verify_grounding_receipt(
                receipt,
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )

    def test_non_admitted_receipts_are_deterministic_and_private(self) -> None:
        for index, label in ((5, "abstain-private"), (6, "refuse-private")):
            with self.subTest(label=label):
                case = self.nonempty_nonadmitted_case(index, label)
                receipts = [
                    build_grounding_receipt(
                        retrieval_request=case["retrieval_request"],
                        candidate=case["candidate"],
                        evidence=self.evidence,
                        retrieval_policy=self.retrieval_policy,
                        grounding_policy=self.grounding_policy,
                    )
                    for _ in range(2)
                ]
                serialized = json.dumps(receipts[0], sort_keys=True)

                self.assertEqual(receipts[0], receipts[1])
                self.assertIsNone(receipts[0]["candidate_response_id"])
                self.assertEqual(receipts[0]["grounded_claims"], [])
                self.assertEqual(receipts[0]["citations"], [])
                self.assertEqual(
                    receipts[0]["input_binding"]["candidate"],
                    {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"},
                )
                self.assertNotIn(case["candidate"]["response_id"], serialized)
                self.assertNotIn(case["candidate"]["claims"][0]["claim_id"], serialized)
                self.assertNotIn(case["candidate"]["claims"][0]["value"], serialized)
                self.assertNotIn("candidate_sha256", serialized)

    def test_non_admitted_claims_do_not_inflate_aggregate_counts(self) -> None:
        changed = copy.deepcopy(self.suite)
        for index, label in ((5, "abstain-report"), (6, "refuse-report")):
            changed["cases"][index] = self.nonempty_nonadmitted_case(index, label)
        path = self.base / "nonempty-nonadmitted-grounding-suite.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        report = run_grounding_evaluation(
            cases_path=path,
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
            output_dir=self.base / "nonempty-nonadmitted",
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checks"]["claim_pass_count"], 3)
        self.assertEqual(report["checks"]["claim_fail_count"], 4)

    def test_non_admitted_receipt_does_not_echo_candidate_ids(self) -> None:
        case = copy.deepcopy(self.suite["cases"][1])
        case["candidate"]["response_id"] = "c2Vuc2l0aXZlLXJlc3BvbnNl"
        case["candidate"]["claims"][0]["claim_id"] = "c2Vuc2l0aXZlLWNsYWlt"

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        serialized = json.dumps(receipt, sort_keys=True)

        self.assertEqual(receipt["disposition"], "QUARANTINE")
        self.assertIsNone(receipt["candidate_response_id"])
        self.assertNotIn(case["candidate"]["response_id"], serialized)
        self.assertNotIn(case["candidate"]["claims"][0]["claim_id"], serialized)
        self.assertNotIn("candidate_sha256", serialized)
        self.assertEqual(
            receipt["input_binding"]["candidate"],
            {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"},
        )
        self.assertEqual(receipt["claim_results"][0]["claim_index"], 1)

    def test_non_admitted_receipt_has_no_low_entropy_candidate_commitment(self) -> None:
        case = copy.deepcopy(self.suite["cases"][1])
        alternate = copy.deepcopy(case)
        alternate["candidate"]["claims"][0]["value"] = "998.000000"

        first = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        second = build_grounding_receipt(
            retrieval_request=alternate["retrieval_request"],
            candidate=alternate["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        self.assertEqual(first["disposition"], "QUARANTINE")
        self.assertEqual(second["disposition"], "QUARANTINE")
        self.assertEqual(
            first["input_binding"]["candidate"],
            second["input_binding"]["candidate"],
        )
        self.assertNotIn("candidate_sha256", json.dumps(first, sort_keys=True))

    def test_receipt_does_not_alias_mutable_candidate_input(self) -> None:
        case = copy.deepcopy(self.suite["cases"][0])
        original_candidate = copy.deepcopy(case["candidate"])
        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        before = json.dumps(receipt, sort_keys=True)
        case["candidate"]["claims"][0]["citation"]["record_sha256"] = "0" * 64

        self.assertEqual(json.dumps(receipt, sort_keys=True), before)
        verify_grounding_receipt(
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=original_candidate,
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

    def test_tampered_receipt_is_rejected(self) -> None:
        case = self.suite["cases"][0]
        receipt = self.receipt_for(0)
        receipt["grounded_claims"][0]["value"] = "ZZZ"

        with self.assertRaisesRegex(IntegrityError, "governed recomputation"):
            verify_grounding_receipt(
                receipt,
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )

    def test_noncanonical_receipt_containers_are_rejected(self) -> None:
        case = self.suite["cases"][0]
        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

    def test_nonfinite_receipt_value_is_an_integrity_error(self) -> None:
        case = self.suite["cases"][0]
        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        receipt["claim_results"][0]["claim_index"] = float("nan")

        with self.assertRaisesRegex(IntegrityError, "structure is invalid"):
            verify_grounding_receipt(
                receipt,
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )
        receipt["reason_codes"] = tuple(receipt["reason_codes"])

        with self.assertRaisesRegex(IntegrityError, "structure is invalid"):
            verify_grounding_receipt(
                receipt,
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )

    def test_non_admitted_candidate_binding_tamper_is_rejected(self) -> None:
        case = self.suite["cases"][1]
        receipt = self.receipt_for(1)
        receipt["input_binding"]["candidate"]["sha256"] = "0" * 64

        with self.assertRaisesRegex(IntegrityError, "governed recomputation"):
            verify_grounding_receipt(
                receipt,
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )

    def test_malformed_candidate_fails_closed(self) -> None:
        case = copy.deepcopy(self.suite["cases"][0])
        case["candidate"]["unexpected"] = True

        with self.assertRaisesRegex(ContractError, "candidate fields"):
            build_grounding_receipt(
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
            )

    def test_unhashable_expected_disposition_fails_with_contract_error(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["expected"]["disposition"] = []
        path = self.base / "malformed-grounding-suite.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "disposition is invalid"):
            run_grounding_evaluation(
                cases_path=path,
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=self.grounding_policy,
                output_dir=self.base / "malformed-grounding",
            )

    def test_grounding_uses_manifest_declared_citation_filename(self) -> None:
        pipeline = build_pipeline_outputs(self.base / "renamed-pipeline")
        original = pipeline / "normalized_events.jsonl"
        renamed = pipeline / "accepted.jsonl"
        original.rename(renamed)
        manifest_path = pipeline / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["normalized_events_jsonl"]["file"] = renamed.name
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        evidence = load_evidence(pipeline)
        case = copy.deepcopy(self.suite["cases"][0])
        for claim in case["candidate"]["claims"]:
            claim["citation"]["artifact"] = renamed.name

        receipt = build_grounding_receipt(
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )

        verify_grounding_receipt(
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
        )
        self.assertEqual(receipt["disposition"], "ADMIT")
        self.assertEqual(receipt["citations"][0]["artifact"], renamed.name)

    def test_policy_cannot_enable_model_or_external_actions(self) -> None:
        original = json.loads(
            (ROOT / "config/grounding_policy.json").read_text(encoding="utf-8")
        )
        for field, message in (
            ("model_execution_enabled", "model execution"),
            ("external_actions_enabled", "external actions"),
        ):
            with self.subTest(field=field):
                changed = dict(original)
                changed[field] = True
                path = self.base / f"{field}.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ContractError, message):
                    load_grounding_policy(path)

    def test_policy_cannot_expand_the_claim_field_boundary(self) -> None:
        changed = json.loads(
            (ROOT / "config/grounding_policy.json").read_text(encoding="utf-8")
        )
        changed["allowed_claim_fields"].append("missing_field")
        changed["allowed_claim_fields"].sort()
        path = self.base / "expanded-fields.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "claim boundary"):
            load_grounding_policy(path)

    def test_policy_rejects_non_string_fields_with_contract_error(self) -> None:
        changed = json.loads(
            (ROOT / "config/grounding_policy.json").read_text(encoding="utf-8")
        )
        changed["allowed_claim_fields"] = [["nested"]]
        path = self.base / "malformed-fields.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "invalid field"):
            load_grounding_policy(path)

    def test_directly_constructed_policy_cannot_expand_claim_fields(self) -> None:
        forged = GroundingPolicy(
            allowed_claim_fields=self.grounding_policy.allowed_claim_fields
            + ("raw_record_sha256",),
            max_claims=self.grounding_policy.max_claims,
            min_claim_failures=self.grounding_policy.min_claim_failures,
            min_claim_passes=self.grounding_policy.min_claim_passes,
            required_case_ids=self.grounding_policy.required_case_ids,
            required_dispositions=self.grounding_policy.required_dispositions,
            sha256=self.grounding_policy.sha256,
        )
        case = self.suite["cases"][0]

        with self.assertRaisesRegex(ContractError, "must be loaded"):
            build_grounding_receipt(
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=forged,
            )

    def test_directly_constructed_policy_cannot_reuse_loaded_digest(self) -> None:
        forged = GroundingPolicy(
            allowed_claim_fields=self.grounding_policy.allowed_claim_fields,
            max_claims=self.grounding_policy.max_claims,
            min_claim_failures=self.grounding_policy.min_claim_failures,
            min_claim_passes=self.grounding_policy.min_claim_passes,
            required_case_ids=self.grounding_policy.required_case_ids,
            required_dispositions=self.grounding_policy.required_dispositions,
            sha256=self.grounding_policy.sha256,
        )
        case = self.suite["cases"][0]

        with self.assertRaisesRegex(ContractError, "must be loaded"):
            build_grounding_receipt(
                retrieval_request=case["retrieval_request"],
                candidate=case["candidate"],
                evidence=self.evidence,
                retrieval_policy=self.retrieval_policy,
                grounding_policy=forged,
            )

    def test_replaced_policy_cannot_retain_loaded_digest(self) -> None:
        mutations = {
            "allowed_claim_fields": self.grounding_policy.allowed_claim_fields[:-1],
            "max_claims": self.grounding_policy.max_claims + 1,
            "min_claim_failures": self.grounding_policy.min_claim_failures + 1,
            "min_claim_passes": self.grounding_policy.min_claim_passes + 1,
            "required_case_ids": self.grounding_policy.required_case_ids[:-1],
            "required_dispositions": self.grounding_policy.required_dispositions[:-1],
            "sha256": "0" * 64,
        }
        case = self.suite["cases"][0]

        for field_name, value in mutations.items():
            with self.subTest(field=field_name):
                forged = replace(self.grounding_policy, **{field_name: value})
                with self.assertRaisesRegex(ContractError, "grounding policy"):
                    build_grounding_receipt(
                        retrieval_request=case["retrieval_request"],
                        candidate=case["candidate"],
                        evidence=self.evidence,
                        retrieval_policy=self.retrieval_policy,
                        grounding_policy=forged,
                    )

    def test_non_json_and_nonfinite_claim_values_fail_closed(self) -> None:
        case = copy.deepcopy(self.suite["cases"][0])
        for value in (float("nan"), {"not-json"}):
            with self.subTest(value=type(value).__name__):
                candidate = copy.deepcopy(case["candidate"])
                candidate["claims"][0]["value"] = value
                with self.assertRaisesRegex(ContractError, "finite JSON values"):
                    build_grounding_receipt(
                        retrieval_request=case["retrieval_request"],
                        candidate=candidate,
                        evidence=self.evidence,
                        retrieval_policy=self.retrieval_policy,
                        grounding_policy=self.grounding_policy,
                    )

    def test_evaluation_passes_all_cases_and_is_deterministic(self) -> None:
        outputs = []
        reports = []
        for name in ("first", "second"):
            output_dir = self.base / name
            reports.append(
                run_grounding_evaluation(
                    cases_path=ROOT / "fixtures/grounding_cases.json",
                    evidence=self.evidence,
                    retrieval_policy=self.retrieval_policy,
                    grounding_policy=self.grounding_policy,
                    output_dir=output_dir,
                )
            )
            outputs.append(output_dir)

        report = reports[0]
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["case_count"], 8)
        self.assertEqual(
            report["disposition_counts"],
            {"ABSTAIN": 1, "ADMIT": 1, "QUARANTINE": 5, "REFUSE": 1},
        )
        self.assertEqual(report["checks"]["expectation_match_count"], 8)
        self.assertEqual(report["checks"]["grounding_integrity_pass_count"], 8)
        self.assertEqual(report["checks"]["candidate_execution_claim_rejected_count"], 1)
        self.assertEqual(report["checks"]["unauthorized_model_execution_count"], 0)
        self.assertEqual(report["checks"]["unauthorized_external_action_count"], 0)
        self.assertEqual(report["checks"]["quarantined_raw_records_exposed_count"], 0)
        for filename in (
            "grounding_receipts.jsonl",
            "grounding_evaluation_report.json",
            "grounding_output_manifest.json",
        ):
            self.assertEqual(
                (outputs[0] / filename).read_bytes(),
                (outputs[1] / filename).read_bytes(),
            )

    def test_expectation_drift_produces_failing_receipt(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["expected"]["disposition"] = "QUARANTINE"
        path = self.base / "changed-grounding-suite.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        report = run_grounding_evaluation(
            cases_path=path,
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
            output_dir=self.base / "failed",
        )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["expectation_match_count"], 7)
        self.assertEqual(report["failures"][0]["case_id"], "valid-claims-are-admitted")

    def test_incomplete_suite_fails_policy_bound_coverage(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"] = [changed["cases"][5]]
        path = self.base / "incomplete-grounding-suite.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        report = run_grounding_evaluation(
            cases_path=path,
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
            output_dir=self.base / "incomplete",
        )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["proof_coverage_status"], "FAIL")

    def test_missing_required_threat_case_fails_coverage(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"] = [
            case
            for case in changed["cases"]
            if case["case_id"] != "tampered-citation-is-quarantined"
        ]
        path = self.base / "missing-threat-case.json"
        path.write_text(json.dumps(changed), encoding="utf-8")

        report = run_grounding_evaluation(
            cases_path=path,
            evidence=self.evidence,
            retrieval_policy=self.retrieval_policy,
            grounding_policy=self.grounding_policy,
            output_dir=self.base / "missing-threat",
        )

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["required_case_count"], 7)
        self.assertEqual(report["checks"]["required_case_total"], 8)


if __name__ == "__main__":
    unittest.main()
