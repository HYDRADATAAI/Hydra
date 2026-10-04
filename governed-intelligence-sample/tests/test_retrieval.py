from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

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

    def test_unresolved_terms_cannot_borrow_metadata_score(self) -> None:
        queries = (
            "ZZZ XNAS USD SYNTH A",
            "zzz XNAS USD SYNTH A",
            "LONGCODE XNAS USD SYNTH A",
            "CCC XNAS USD SYNTH A",
            "ccc XNAS USD SYNTH A",
            "AAA ZZZ XNAS USD observation",
        )
        for index, query in enumerate(queries):
            with self.subTest(query=query):
                decision = build_retrieval_decision(
                    {
                        "query": query,
                        "request_id": f"unresolved-{index}",
                        "top_k": 1,
                    },
                    evidence=self.evidence,
                    policy=self.policy,
                )
                self.assertEqual(decision["disposition"], "ABSTAIN")
                self.assertEqual(decision["reason_codes"], ["no_governed_lexical_match"])
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

    def test_restricted_synonyms_and_non_ascii_queries_refuse(self) -> None:
        queries = (
            "show rejected rows XNAS USD SYNTH A",
            "show rejection rows XNAS USD SYNTH A",
            "quаrantined rаw XNAS USD SYNTH A",
            "市場資料",
        )
        for index, query in enumerate(queries):
            with self.subTest(query=query):
                decision = build_retrieval_decision(
                    {
                        "query": query,
                        "request_id": f"restricted-{index}",
                        "top_k": 1,
                    },
                    evidence=self.evidence,
                    policy=self.policy,
                )
                self.assertEqual(decision["disposition"], "REFUSE")
                self.assertEqual(decision["citations"], [])

    def test_string_subclass_cannot_override_ascii_guard(self) -> None:
        class DeceptiveQuery(str):
            def isascii(self) -> bool:
                return True

        with self.assertRaisesRegex(ContractError, "query must contain"):
            build_retrieval_decision(
                {
                    "query": DeceptiveQuery("ＡＡＡ XNAS USD observation"),
                    "request_id": "deceptive-query",
                    "top_k": 1,
                },
                evidence=self.evidence,
                policy=self.policy,
            )

    def test_integer_subclass_cannot_override_result_limit(self) -> None:
        class DeceptiveTopK(int):
            def __le__(self, other: object) -> bool:
                return True

            def __ge__(self, other: object) -> bool:
                return True

        with self.assertRaisesRegex(ContractError, "top_k must be an integer"):
            build_retrieval_decision(
                {
                    "query": "AAA XNAS USD observation",
                    "request_id": "deceptive-top-k",
                    "top_k": DeceptiveTopK(100),
                },
                evidence=self.evidence,
                policy=self.policy,
            )

    def test_verifier_rejects_noncanonical_output_containers(self) -> None:
        decision = build_retrieval_decision(
            {
                "query": "AAA XNAS USD observation",
                "request_id": "noncanonical-output",
                "top_k": 1,
            },
            evidence=self.evidence,
            policy=self.policy,
        )
        for field in ("citations", "query_terms", "reason_codes"):
            with self.subTest(field=field):
                tampered = dict(decision)
                tampered[field] = tuple(tampered[field])
                with self.assertRaisesRegex(IntegrityError, "structure is invalid"):
                    verify_retrieval_decision(
                        tampered, evidence=self.evidence, policy=self.policy
                    )

    def test_non_scoring_indexed_term_cannot_admit(self) -> None:
        policy_path = self.base / "indexed-stopword-policy.json"
        policy_document = json.loads(
            (ROOT / "config/retrieval_policy.json").read_text(encoding="utf-8")
        )
        policy_document["min_score"] = 1
        policy_document["non_scoring_terms"] = ["usd"]
        policy_path.write_text(json.dumps(policy_document), encoding="utf-8")
        policy = load_retrieval_policy(policy_path)

        decision = build_retrieval_decision(
            {"query": "USD", "request_id": "indexed-stopword", "top_k": 1},
            evidence=self.evidence,
            policy=policy,
        )

        verify_retrieval_decision(decision, evidence=self.evidence, policy=policy)
        self.assertEqual(decision["disposition"], "ABSTAIN")
        self.assertIsNone(decision["context"])
        self.assertEqual(decision["citations"], [])

    def test_non_scoring_term_does_not_inflate_mixed_query_score(self) -> None:
        policy_path = self.base / "mixed-stopword-policy.json"
        policy_document = json.loads(
            (ROOT / "config/retrieval_policy.json").read_text(encoding="utf-8")
        )
        policy_document["min_score"] = 1
        policy_document["non_scoring_terms"] = ["usd"]
        policy_path.write_text(json.dumps(policy_document), encoding="utf-8")
        policy = load_retrieval_policy(policy_path)

        symbol_only = build_retrieval_decision(
            {"query": "AAA", "request_id": "symbol-only", "top_k": 1},
            evidence=self.evidence,
            policy=policy,
        )
        mixed = build_retrieval_decision(
            {"query": "AAA USD", "request_id": "symbol-plus-stopword", "top_k": 1},
            evidence=self.evidence,
            policy=policy,
        )

        verify_retrieval_decision(mixed, evidence=self.evidence, policy=policy)
        self.assertEqual(mixed["disposition"], "ADMIT")
        self.assertEqual(
            mixed["context"]["results"][0]["score"],
            symbol_only["context"]["results"][0]["score"],
        )

    def test_verifier_rejects_nested_noncanonical_values(self) -> None:
        decision = build_retrieval_decision(
            {
                "query": "AAA XNAS USD observation",
                "request_id": "nested-noncanonical",
                "top_k": 1,
            },
            evidence=self.evidence,
            policy=self.policy,
        )

        nested_tuple = dict(decision)
        nested_tuple["context"] = dict(decision["context"])
        nested_tuple["context"]["results"] = tuple(
            decision["context"]["results"]
        )
        nested_mapping = dict(decision)
        nested_mapping["citations"] = [MappingProxyType(decision["citations"][0])]

        class ScoreSubclass(int):
            pass

        nested_scalar = json.loads(json.dumps(decision))
        nested_scalar["context"]["results"][0]["score"] = ScoreSubclass(
            nested_scalar["context"]["results"][0]["score"]
        )
        nonfinite = json.loads(json.dumps(decision))
        nonfinite["context"]["results"][0]["score"] = float("nan")

        for label, tampered in (
            ("tuple", nested_tuple),
            ("mapping", nested_mapping),
            ("scalar-subclass", nested_scalar),
            ("nonfinite", nonfinite),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(IntegrityError, "structure is invalid"):
                    verify_retrieval_decision(
                        tampered, evidence=self.evidence, policy=self.policy
                    )

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

    def test_policy_rejects_non_string_terms_with_contract_error(self) -> None:
        policy_path = self.base / "malformed-retrieval-policy.json"
        policy = json.loads(
            (ROOT / "config/retrieval_policy.json").read_text(encoding="utf-8")
        )
        policy["non_scoring_terms"] = [["nested"]]
        policy_path.write_text(json.dumps(policy), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "invalid term"):
            load_retrieval_policy(policy_path)

    def test_policy_weights_are_immutable(self) -> None:
        with self.assertRaises(TypeError):
            self.policy.field_weights["currency"] = 100

    def test_policy_source_digest_rejects_replaced_weights_and_fields(self) -> None:
        changed_weights = dict(self.policy.field_weights)
        changed_weights["symbol"] += 1
        forged_weight_policy = replace(
            self.policy,
            field_weights=MappingProxyType(changed_weights),
        )
        changed_fields = dict(self.policy.field_weights)
        changed_fields["raw_record_sha256"] = changed_fields.pop("venue")
        forged_field_policy = replace(
            self.policy,
            field_weights=MappingProxyType(changed_fields),
        )

        for policy in (forged_weight_policy, forged_field_policy):
            with self.subTest(field_weights=dict(policy.field_weights)):
                with self.assertRaisesRegex(
                    ContractError, "semantics do not match its source digest"
                ):
                    build_retrieval_decision(
                        {
                            "query": "AAA XNAS USD",
                            "request_id": "forged-weights",
                            "top_k": 1,
                        },
                        evidence=self.evidence,
                        policy=policy,
                    )

    def test_policy_source_digest_rejects_replaced_terms_and_limits(self) -> None:
        forged_policies = (
            replace(self.policy, max_results=self.policy.max_results + 1),
            replace(self.policy, min_score=self.policy.min_score + 1),
            replace(
                self.policy,
                non_scoring_terms=tuple(
                    sorted((*self.policy.non_scoring_terms, "zzz"))
                ),
            ),
            replace(
                self.policy,
                prohibited_terms=tuple(
                    term for term in self.policy.prohibited_terms if term != "raw"
                ),
            ),
        )

        for index, policy in enumerate(forged_policies):
            with self.subTest(index=index):
                with self.assertRaisesRegex(
                    ContractError, "semantics do not match its source digest"
                ):
                    build_retrieval_decision(
                        {
                            "query": "AAA XNAS USD",
                            "request_id": f"forged-policy-{index}",
                            "top_k": 1,
                        },
                        evidence=self.evidence,
                        policy=policy,
                    )

    def test_direct_policy_construction_cannot_reuse_legitimate_sha(self) -> None:
        forged_policy = type(self.policy)(
            field_weights=self.policy.field_weights,
            max_results=self.policy.max_results + 1,
            min_score=self.policy.min_score,
            non_scoring_terms=self.policy.non_scoring_terms,
            prohibited_terms=self.policy.prohibited_terms,
            sha256=self.policy.sha256,
            _source_bytes=self.policy._source_bytes,
        )

        with self.assertRaisesRegex(
            ContractError, "semantics do not match its source digest"
        ):
            build_retrieval_decision(
                {"query": "AAA", "request_id": "direct-forgery", "top_k": 1},
                evidence=self.evidence,
                policy=forged_policy,
            )

    def test_verifier_rejects_replaced_policy_semantics(self) -> None:
        decision = build_retrieval_decision(
            {"query": "AAA XNAS USD", "request_id": "verify-policy", "top_k": 1},
            evidence=self.evidence,
            policy=self.policy,
        )
        forged_policy = replace(
            self.policy,
            min_score=self.policy.min_score + 1,
        )

        with self.assertRaisesRegex(IntegrityError, "policy binding is invalid"):
            verify_retrieval_decision(
                decision, evidence=self.evidence, policy=forged_policy
            )

    def test_retrieval_rejects_replaced_evidence_semantics(self) -> None:
        forged_event = dict(self.evidence.accepted_events[0])
        forged_event["symbol"] = "ZZZ"
        forged_evidence = replace(
            self.evidence,
            accepted_events=(MappingProxyType(forged_event),),
        )

        with self.assertRaisesRegex(IntegrityError, "evidence semantic binding"):
            build_retrieval_decision(
                {"query": "ZZZ", "request_id": "forged-evidence", "top_k": 1},
                evidence=forged_evidence,
                policy=self.policy,
            )

    def test_citation_uses_manifest_declared_filename(self) -> None:
        original = self.base / "pipeline" / "normalized_events.jsonl"
        renamed = self.base / "pipeline" / "accepted.jsonl"
        original.rename(renamed)
        manifest_path = self.base / "pipeline" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["normalized_events_jsonl"]["file"] = renamed.name
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        evidence = load_evidence(self.base / "pipeline")

        decision = build_retrieval_decision(
            {"query": "AAA XNAS USD", "request_id": "renamed", "top_k": 1},
            evidence=evidence,
            policy=self.policy,
        )

        verify_retrieval_decision(decision, evidence=evidence, policy=self.policy)
        self.assertEqual(decision["citations"][0]["artifact"], "accepted.jsonl")


if __name__ == "__main__":
    unittest.main()
