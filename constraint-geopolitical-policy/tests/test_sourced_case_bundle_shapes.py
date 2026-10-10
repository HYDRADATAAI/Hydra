import json
import unittest
from pathlib import Path

from hydra_constraint_policy.case_studies import (
    CaseStudyValidationError,
    validate_sourced_case_bundle,
)


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "sourced_historical_cases.json"
)


class SourcedCaseBundleShapeTests(unittest.TestCase):
    def load_bundle(self):
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))

    def assert_invalid_bundle(self, bundle):
        with self.assertRaises(CaseStudyValidationError):
            validate_sourced_case_bundle(bundle)

    def test_non_object_bundle_is_rejected(self):
        for bundle in (None, [], "bundle"):
            with self.subTest(bundle=bundle):
                self.assert_invalid_bundle(bundle)

    def test_top_level_collections_and_members_are_checked(self):
        mutations = (
            ("sources is null", lambda b: b.update(sources=None)),
            ("sources is an object", lambda b: b.update(sources={})),
            ("source item is null", lambda b: b["sources"].__setitem__(0, None)),
            ("cases is null", lambda b: b.update(cases=None)),
            ("cases is an object", lambda b: b.update(cases={})),
            ("case item is null", lambda b: b["cases"].__setitem__(0, None)),
        )
        for label, mutate in mutations:
            with self.subTest(shape=label):
                bundle = self.load_bundle()
                mutate(bundle)
                self.assert_invalid_bundle(bundle)

    def test_nested_collections_and_members_are_checked(self):
        mutations = (
            ("events is null", lambda b: b["cases"][0].update(events=None)),
            ("event item is null", lambda b: b["cases"][0]["events"].__setitem__(0, None)),
            ("observations is null", lambda b: b["cases"][2].update(observations=None)),
            (
                "observation item is null",
                lambda b: b["cases"][2]["observations"].__setitem__(0, None),
            ),
            (
                "relations is null",
                lambda b: b["cases"][0]["events"][0].update(relations=None),
            ),
            (
                "relation item is null",
                lambda b: b["cases"][0]["events"][0]["relations"].__setitem__(0, None),
            ),
            (
                "source_ids is null",
                lambda b: b["cases"][0]["events"][0].update(source_ids=None),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(shape=label):
                bundle = self.load_bundle()
                mutate(bundle)
                self.assert_invalid_bundle(bundle)

    def test_missing_required_object_fields_are_rejected_as_domain_errors(self):
        mutations = (
            ("source timestamp missing", lambda b: b["sources"][0].pop("published_at")),
            (
                "event statement missing",
                lambda b: b["cases"][0]["events"][0].pop("statement"),
            ),
            (
                "relation confidence missing",
                lambda b: b["cases"][0]["events"][0]["relations"][0].pop("confidence"),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(shape=label):
                bundle = self.load_bundle()
                mutate(bundle)
                self.assert_invalid_bundle(bundle)

    def test_omitted_top_level_collections_keep_empty_defaults(self):
        bundle = {"evidence_digest_scope": "sha256(normalized_evidence UTF-8)"}
        self.assertIsNone(validate_sourced_case_bundle(bundle))


if __name__ == "__main__":
    unittest.main()
