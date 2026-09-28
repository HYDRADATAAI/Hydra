from __future__ import annotations

import copy
import unittest

from hydra_constraint_t1_raw.evidence_lineage_binding import (
    EvidenceLineageBindingError,
    build_evidence_lineage_binding,
    select_bound_evidence,
)


class EvidenceLineageBindingTests(unittest.TestCase):
    def setUp(self):
        self.slice_id="SLICE-X"
        self.lineage={
            "release_id":"REL-X",
            "release_sha256":"a"*64,
            "source_count":2,
            "ordinary_current_source_set_ready":True,
            "strict_historical_replay_ready":False,
            "historical_availability_backdated":False,
            "canonical_evidence_admission_promoted":False,
            "canonical_t5_t6_admission_promoted":False,
            "historical_replay_blocker":"BLOCK",
            "members":[
                {
                    "source_id":"SRC-A","source_version_id":"SV-A","artifact_sha256":"b"*64,
                    "receipt_sha256":"c"*64,"available_at":"2026-09-28T12:00:00Z",
                    "acquired_at":"2026-09-28T12:00:00Z","ordinary_t2_eligible":True,
                    "processing_disposition":"ELIGIBLE",
                },
                {
                    "source_id":"SRC-B","source_version_id":"SV-B","artifact_sha256":"d"*64,
                    "receipt_sha256":"e"*64,"available_at":"2026-09-28T13:00:00Z",
                    "acquired_at":"2026-09-28T13:00:00Z","ordinary_t2_eligible":True,
                    "processing_disposition":"ELIGIBLE",
                },
            ],
        }
        self.docs=[
            {
                "record_id":"REC-1","slice_id":self.slice_id,
                "evidence":[
                    {"evidence_id":"EV-A","source_id":"SRC-A","proposition":"A"},
                    {"evidence_id":"EV-OLD","source_id":"SRC-OLD","proposition":"old"},
                ],
            },
            {
                "record_id":"REC-2","slice_id":self.slice_id,
                "evidence":[{"evidence_id":"EV-B","source_id":"SRC-B","proposition":"B"}],
            },
        ]

    def test_build_binds_exact_versions_and_preserves_unbound(self):
        packet=build_evidence_lineage_binding(
            source_lineage=self.lineage,evidence_documents=self.docs,expected_slice_id=self.slice_id
        )
        self.assertEqual(3,packet["reviewed_evidence_record_count"])
        self.assertEqual(2,packet["bound_evidence_count"])
        self.assertEqual(1,packet["unbound_evidence_count"])
        self.assertTrue(packet["active_source_coverage_complete"])
        self.assertEqual("SV-A",packet["bound_evidence"][0]["source_version_id"])
        self.assertEqual("EV-OLD",packet["unbound_evidence"][0]["evidence_id"])
        self.assertFalse(packet["strict_historical_replay_ready"])

    def test_no_lookahead_selection(self):
        packet=build_evidence_lineage_binding(
            source_lineage=self.lineage,evidence_documents=self.docs,expected_slice_id=self.slice_id
        )
        self.assertEqual([],select_bound_evidence(
            packet=packet,source_lineage=self.lineage,evidence_documents=self.docs,
            expected_slice_id=self.slice_id,as_of="2026-09-28T11:59:59Z"
        ))
        self.assertEqual(["EV-A"],[x["evidence_id"] for x in select_bound_evidence(
            packet=packet,source_lineage=self.lineage,evidence_documents=self.docs,
            expected_slice_id=self.slice_id,as_of="2026-09-28T12:00:00Z"
        )])

    def test_duplicate_evidence_id_rejected(self):
        bad=copy.deepcopy(self.docs)
        bad[1]["evidence"][0]["evidence_id"]="EV-A"
        with self.assertRaisesRegex(EvidenceLineageBindingError,"duplicate evidence_id"):
            build_evidence_lineage_binding(
                source_lineage=self.lineage,evidence_documents=bad,expected_slice_id=self.slice_id
            )

    def test_source_backdating_rejected(self):
        bad=copy.deepcopy(self.lineage)
        bad["members"][0]["available_at"]="2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(EvidenceLineageBindingError,"conservative availability drift"):
            build_evidence_lineage_binding(
                source_lineage=bad,evidence_documents=self.docs,expected_slice_id=self.slice_id
            )

    def test_replay_promotion_rejected(self):
        bad=copy.deepcopy(self.lineage)
        bad["strict_historical_replay_ready"]=True
        with self.assertRaisesRegex(EvidenceLineageBindingError,"strict historical replay"):
            build_evidence_lineage_binding(
                source_lineage=bad,evidence_documents=self.docs,expected_slice_id=self.slice_id
            )


if __name__=="__main__":
    unittest.main()
