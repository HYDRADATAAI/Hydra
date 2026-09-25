import copy
import json
import unittest
from pathlib import Path

from hydra_constraint_policy.case_studies import (
    CaseStudyValidationError,
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

    def test_physical_binding_status_stays_explicit(self):
        bundle=self.load_raw()
        bundle["cases"][0]["binding_status"]="BOUND"
        with self.assertRaisesRegex(CaseStudyValidationError,"binding status"):
            validate_sourced_case_bundle(bundle)

    def test_duplicate_event_id_fails_closed(self):
        bundle=self.load_raw()
        duplicate=copy.deepcopy(bundle["cases"][0]["events"][0])
        bundle["cases"][1]["events"].append(duplicate)
        with self.assertRaisesRegex(CaseStudyValidationError,"duplicate or missing event_id"):
            validate_sourced_case_bundle(bundle)


if __name__=="__main__":
    unittest.main()
