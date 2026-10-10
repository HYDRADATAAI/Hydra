from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from hydra_t6_failclosed.native_t5_t6_bridge import (
    NativeT5T6BridgeError,
    build_native_t5_t6_handoff,
)
from hydra_t6_failclosed.native_t5_t6_bridge_v2 import build_native_t5_t6_handoff_v2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"
INVALID_BOOLEAN_VALUES = ("false", "true", 0, 1, None, [], {})


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class NativeT5T6BridgeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposals = load(BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json")
        cls.overlay = load(BASE / "HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V002_20260926.json")

    def build(self, proposals=None, overlay=None):
        return build_native_t5_t6_handoff_v2(
            self.proposals if proposals is None else proposals,
            self.overlay if overlay is None else overlay,
            handoff_id="AIDC-FIRST-SLICE-NATIVE-T5-T6-V2-20261003",
            created_at="2026-10-03T18:30:00Z",
        )

    def build_v1(self, proposals=None, overlay=None):
        return build_native_t5_t6_handoff(
            self.proposals if proposals is None else proposals,
            self.overlay if overlay is None else overlay,
            handoff_id="AIDC-FIRST-SLICE-NATIVE-T5-T6-V2-20261003",
            created_at="2026-10-03T18:30:00Z",
        )

    def assert_same_bridge_error(self, proposals, overlay):
        with self.assertRaises(NativeT5T6BridgeError) as v1_error:
            self.build_v1(proposals=proposals, overlay=overlay)
        with self.assertRaises(NativeT5T6BridgeError) as v2_error:
            self.build(proposals=proposals, overlay=overlay)
        self.assertEqual(str(v2_error.exception), str(v1_error.exception))

    def test_valid_inputs_preserve_v1_mapping(self):
        self.assertEqual(self.build(), self.build_v1())

    def test_valid_true_inputs_preserve_v1_mapping(self):
        proposals = deepcopy(self.proposals)
        overlay = deepcopy(self.overlay)
        proposals["candidates"][0]["ordinary_t6_eligible"] = True
        overlay["candidates"][0]["ordinary_t6_eligible"] = True
        self.assertEqual(
            self.build(proposals=proposals, overlay=overlay),
            self.build_v1(proposals=proposals, overlay=overlay),
        )

    def test_structural_errors_are_delegated_to_v1(self):
        proposals = deepcopy(self.proposals)
        del proposals["candidates"][0]["ordinary_t6_eligible"]
        self.assert_same_bridge_error(proposals, self.overlay)

        overlay = deepcopy(self.overlay)
        del overlay["candidates"][0]["ordinary_t6_eligible"]
        self.assert_same_bridge_error(self.proposals, overlay)

    def test_proposal_eligibility_must_be_a_boolean(self):
        for value in INVALID_BOOLEAN_VALUES:
            with self.subTest(value=value):
                proposals = deepcopy(self.proposals)
                proposals["candidates"][0]["ordinary_t6_eligible"] = value
                with self.assertRaisesRegex(NativeT5T6BridgeError, "must be a boolean"):
                    self.build(proposals=proposals)

    def test_overlay_eligibility_must_be_a_boolean(self):
        for value in INVALID_BOOLEAN_VALUES:
            with self.subTest(value=value):
                overlay = deepcopy(self.overlay)
                overlay["candidates"][0]["ordinary_t6_eligible"] = value
                with self.assertRaisesRegex(NativeT5T6BridgeError, "must be a boolean"):
                    self.build(overlay=overlay)

    def test_matching_truthy_strings_are_rejected_instead_of_promoted(self):
        proposals = deepcopy(self.proposals)
        overlay = deepcopy(self.overlay)
        proposals["candidates"][0]["ordinary_t6_eligible"] = "false"
        overlay["candidates"][0]["ordinary_t6_eligible"] = "false"
        with self.assertRaisesRegex(NativeT5T6BridgeError, "must be a boolean"):
            self.build(proposals=proposals, overlay=overlay)


if __name__ == "__main__":
    unittest.main()
