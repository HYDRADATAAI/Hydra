import copy
import json
import unittest
from pathlib import Path

from hydra_constraint_policy.case_studies import (
    CaseStudyValidationError,
    events_from_sourced_case_bundle,
    load_sourced_case_bundle,
    validate_sourced_case_bundle,
)


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "sourced_historical_cases.json"
)


class SourcedCaseStudyTests(unittest.TestCase):
    def load_raw(self):
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def test_committed_bundle_validates(self):
        bundle=load_sourced_case_bundle(DATA_PATH)
        self.assertEqual(4,len(bundle["cases"]))
        self.assertEqual(7,len(bundle["sources"]))

    def test_naive_temporal_clocks_are_rejected(self):
        cases = [
            ("source published_at", ("sources", 0, "published_at")),
            ("source available_at", ("sources", 0, "available_at")),
            ("event known_at", ("cases", 0, "events", 0, "known_at")),
            ("event effective_at", ("cases", 0, "events", 0, "effective_at")),
            ("event observed_at", ("cases", 0, "events", 0, "observed_at")),
            ("event resolved_at", ("cases", 0, "events", 0, "resolved_at")),
            ("observation known_at", ("cases", 2, "observations", 0, "known_at")),
            ("observation observed_at", ("cases", 2, "observations", 0, "observed_at")),
        ]
        for label, path in cases:
            with self.subTest(clock=label):
                bundle = self.load_raw()
                target = bundle
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = "2022-01-01T00:00:00"
                with self.assertRaisesRegex(
                    CaseStudyValidationError, "timezone-aware timestamp required"
                ):
                    validate_sourced_case_bundle(bundle)

    def test_absent_and_null_optional_event_clocks_materialize_as_none(self):
        clocks = ("effective_at", "observed_at", "resolved_at")
        for mode in ("absent", "null"):
            with self.subTest(mode=mode):
                bundle = self.load_raw()
                raw_event = bundle["cases"][0]["events"][0]
                event_id = raw_event["event_id"]
                for clock in clocks:
                    if mode == "absent":
                        raw_event.pop(clock, None)
                    else:
                        raw_event[clock] = None

                validate_sourced_case_bundle(bundle)
                events = events_from_sourced_case_bundle(bundle)
                event = next(item for item in events if item.event_id == event_id)
                for clock in clocks:
                    self.assertIsNone(getattr(event.temporal, clock))

    def test_malformed_event_clock_raises_validation_error(self):
        bundle = self.load_raw()
        bundle["cases"][0]["events"][0]["known_at"] = None
        with self.assertRaisesRegex(CaseStudyValidationError, "invalid timestamp"):
            validate_sourced_case_bundle(bundle)

    def test_empty_effective_at_is_rejected(self):
        bundle = self.load_raw()
        bundle["cases"][0]["events"][0]["effective_at"] = ""
        with self.assertRaisesRegex(CaseStudyValidationError, "invalid timestamp"):
            validate_sourced_case_bundle(bundle)

    def test_empty_event_observed_at_is_rejected(self):
        bundle = self.load_raw()
        bundle["cases"][0]["events"][0]["observed_at"] = ""
        with self.assertRaisesRegex(CaseStudyValidationError, "invalid timestamp"):
            validate_sourced_case_bundle(bundle)

    def test_empty_resolved_at_is_rejected(self):
        bundle = self.load_raw()
        bundle["cases"][0]["events"][0]["resolved_at"] = ""
        with self.assertRaisesRegex(CaseStudyValidationError, "invalid timestamp"):
            validate_sourced_case_bundle(bundle)

    def test_offset_source_timestamp_is_accepted(self):
        bundle = self.load_raw()
        bundle["sources"][0]["published_at"] = "2022-01-01T03:00:00+03:00"
        validate_sourced_case_bundle(bundle)

    def test_case_families_are_present(self):
        bundle=load_sourced_case_bundle(DATA_PATH)
        self.assertEqual(
            {
                "bis-semiconductor-controls-2022",
                "eu-russian-oil-import-restrictions-2022",
                "suez-ever-given-2021",
                "us-chips-act-2022",
            },
            {case["case_id"] for case in bundle["cases"]},
        )

    def test_committed_cases_use_canonical_binding_status(self):
        bundle=load_sourced_case_bundle(DATA_PATH)
        self.assertEqual(
            {"BOUND_MINIMAL_CANONICAL_SUBGRAPH"},
            {case["binding_status"] for case in bundle["cases"]},
        )
        self.assertTrue(all(
            event.get("relations")
            for case in bundle["cases"]
            for event in case["events"]
        ))

    def test_materializes_executable_historical_events(self):
        bundle=load_sourced_case_bundle(DATA_PATH)
        events=events_from_sourced_case_bundle(bundle)
        self.assertEqual(7,len(events))
        self.assertTrue(all(e.relations for e in events))
        self.assertTrue(all(e.metadata["source_uris"] for e in events))

    def test_evidence_digest_tampering_fails_closed(self):
        bundle=self.load_raw()
        bundle["sources"][0]["normalized_evidence"] += " tampered"
        with self.assertRaisesRegex(CaseStudyValidationError,"digest mismatch"):
            validate_sourced_case_bundle(bundle)

    def test_future_source_cannot_support_earlier_known_at(self):
        bundle=self.load_raw()
        bad=copy.deepcopy(bundle)
        bad["sources"][0]["available_at"]="2022-10-08T00:00:00Z"
        with self.assertRaisesRegex(CaseStudyValidationError,"was not available by KNOWN_AT"):
            validate_sourced_case_bundle(bad)

    def test_unknown_source_reference_fails_closed(self):
        bundle=self.load_raw()
        bundle["cases"][0]["events"][0]["source_ids"]=["missing-source"]
        with self.assertRaisesRegex(CaseStudyValidationError,"unknown source"):
            validate_sourced_case_bundle(bundle)

    def test_unsupported_physical_binding_status_fails(self):
        bundle=self.load_raw()
        bundle["cases"][0]["binding_status"]="MADE_UP"
        with self.assertRaisesRegex(CaseStudyValidationError,"binding status"):
            validate_sourced_case_bundle(bundle)

    def test_bound_event_without_relation_fails(self):
        bundle=self.load_raw()
        bundle["cases"][0]["events"][0]["relations"]=[]
        with self.assertRaisesRegex(CaseStudyValidationError,"no canonical physical relations"):
            validate_sourced_case_bundle(bundle)

    def test_duplicate_event_id_fails_closed(self):
        bundle=self.load_raw()
        duplicate=copy.deepcopy(bundle["cases"][0]["events"][0])
        bundle["cases"][1]["events"].append(duplicate)
        with self.assertRaisesRegex(CaseStudyValidationError,"duplicate or missing event_id"):
            validate_sourced_case_bundle(bundle)


if __name__=="__main__":
    unittest.main()
