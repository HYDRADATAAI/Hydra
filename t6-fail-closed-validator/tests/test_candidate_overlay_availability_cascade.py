"""Changed-input regression for candidate-overlay availability cascades."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

from hydra_t6_failclosed.first_slice_shadow_replay import build_shadow_snapshot


# Load the canonical first-slice fixture setup by sibling path. Several suites
# use a top-level package named tests, so avoid relying on its import identity.
_spec = importlib.util.spec_from_file_location(
    "hydra_candidate_overlay_availability_fixture",
    Path(__file__).with_name("test_first_slice_outcome_shadow_replay.py"),
)
existing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(existing)


class CandidateOverlayAvailabilityCascadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        existing.FirstSliceOutcomeShadowReplayTests.setUpClass()
        cls.fixtures = existing.FirstSliceOutcomeShadowReplayTests

    def test_candidate_overlay_availability_cascades_to_dependents(self):
        fixtures = self.fixtures
        cutoff = "2026-09-26T12:47:00Z"
        inputs = {
            "claim_registry": copy.deepcopy(fixtures.claims),
            "candidates": copy.deepcopy(fixtures.candidates),
            "relief_paths": copy.deepcopy(fixtures.relief),
            "beneficiaries": copy.deepcopy(fixtures.beneficiaries),
            "outcomes": copy.deepcopy(fixtures.outcomes),
            "candidate_overlay": copy.deepcopy(fixtures.overlay),
        }
        target_candidate = "T5C-AIDC-US-INTERCONNECTION-THROUGHPUT-001"
        removed_ids = {
            "constraint_candidate_ids": (target_candidate,),
            "relief_path_ids": ("REL-AIDC-001", "REL-AIDC-002", "REL-AIDC-003"),
            "beneficiary_relationship_ids": ("BEN-AIDC-VERTIV-POWER-RELIEF-001",),
        }

        baseline = build_shadow_snapshot(as_of=cutoff, **inputs)
        for field, identities in removed_ids.items():
            for identity in identities:
                self.assertIn(identity, baseline[field])

        overlay_row = next(
            row for row in inputs["candidate_overlay"]["candidates"]
            if row["constraint_candidate_id"] == target_candidate
        )
        self.assertEqual(cutoff, overlay_row["available_at"])

        expected = copy.deepcopy(baseline)
        for field, identities in removed_ids.items():
            expected[field] = [
                identity for identity in expected[field] if identity not in identities
            ]

        # Change only the target candidate overlay row. Its three relief paths
        # and beneficiary disappear with it; unrelated candidates, claims, and
        # the independently visible outcome must remain exactly as before.
        overlay_row["available_at"] = "2026-09-26T12:47:01Z"
        changed = build_shadow_snapshot(as_of=cutoff, **inputs)
        self.assertEqual(expected, changed)


if __name__ == "__main__":
    unittest.main()
