from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_policy.claims import (
    ClaimEvidenceError,
    load_claim_revision_bundle,
)


class ClaimBundleShapeValidationTests(unittest.TestCase):
    def load_payload(self, payload: object):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claims.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_claim_revision_bundle(path)

    def test_non_object_roots_raise_domain_error(self) -> None:
        for payload in (None, [], False, 1, "claims"):
            with self.subTest(payload=payload), self.assertRaises(ClaimEvidenceError):
                self.load_payload(payload)

    def test_claim_and_revision_containers_require_arrays_of_objects(self) -> None:
        malformed = (
            {"claims": None},
            {"claims": {}},
            {"claims": [None]},
            {"revisions": False},
            {"revisions": "revision"},
            {"revisions": [0]},
        )
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ClaimEvidenceError):
                self.load_payload(payload)

    def test_evidence_requires_an_array_of_objects(self) -> None:
        malformed = (
            {"claims": [{"claim_id": "C1", "proposition": "P", "evidence": None}]},
            {"claims": [{"claim_id": "C1", "proposition": "P", "evidence": [None]}]},
        )
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ClaimEvidenceError):
                self.load_payload(payload)

    def test_missing_fields_and_invalid_enums_raise_domain_error(self) -> None:
        malformed = (
            {"claims": [{"proposition": "P", "evidence": []}]},
            {
                "claims": [{
                    "claim_id": "C1",
                    "proposition": "P",
                    "evidence": [{
                        "evidence_id": "E1",
                        "document_id": "D1",
                        "known_at": "2026-01-01T00:00:00Z",
                        "stance": "unsupported",
                        "attributed_to": "source",
                        "statement": "statement",
                    }],
                }],
            },
            {
                "revisions": [{
                    "revision_id": "R1",
                    "prior_document_id": "D1",
                    "revision_document_id": "D2",
                    "known_at": "2026-01-01T00:00:00Z",
                    "relation": "unsupported",
                    "scope": "scope",
                }],
            },
        )
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(ClaimEvidenceError):
                self.load_payload(payload)


if __name__ == "__main__":
    unittest.main()
