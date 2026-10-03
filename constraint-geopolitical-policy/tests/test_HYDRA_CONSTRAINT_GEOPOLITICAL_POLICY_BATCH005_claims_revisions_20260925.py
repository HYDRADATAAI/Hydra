import unittest
from datetime import datetime, timezone
from pathlib import Path

from hydra_constraint_policy.claims import (
    ClaimState,
    RevisionRelation,
    available_claim_evidence,
    claim_state_as_of,
    load_claim_revision_bundle,
    revisions_as_of,
)
from hydra_constraint_policy.case_studies import load_sourced_case_bundle


ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH005_CONTESTED_REVISION_FIXTURES_20260925.json"
BATCH3=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH003_SOURCED_HISTORICAL_CASES_20260925.json"
UTC=timezone.utc


class Batch005ClaimsRevisionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claims,cls.revisions=load_claim_revision_bundle(FIXTURE)

    def test_fixture_shape(self):
        self.assertEqual(1,len(self.claims))
        self.assertEqual(1,len(self.revisions))

    def test_wto_implementation_claim_is_contested_not_adjudicated(self):
        claim=self.claims[0]
        before=datetime(2015,5,20,12,0,tzinfo=UTC)
        after=datetime(2015,5,20,23,59,59,tzinfo=UTC)
        self.assertEqual(ClaimState.NO_AVAILABLE_EVIDENCE,claim_state_as_of(claim,before))
        self.assertEqual(ClaimState.CONTESTED,claim_state_as_of(claim,after))
        evidence=available_claim_evidence(claim,after)
        self.assertEqual({"China","United States"},{e.attributed_to for e in evidence})
        self.assertEqual({"supporting","opposing"},{e.stance.value for e in evidence})

    def test_panama_revision_is_modification_not_retraction(self):
        revision=self.revisions[0]
        self.assertEqual(RevisionRelation.MODIFIES,revision.relation)
        before=datetime(2023,12,15,12,0,tzinfo=UTC)
        after=datetime(2023,12,15,23,59,59,tzinfo=UTC)
        self.assertEqual((),revisions_as_of(self.revisions,before))
        self.assertEqual((revision,),revisions_as_of(self.revisions,after))

    def test_claim_and_revision_documents_exist_in_sourced_batch(self):
        bundle=load_sourced_case_bundle(BATCH3)
        source_ids={s["source_id"] for s in bundle["sources"]}
        for claim in self.claims:
            for evidence in claim.evidence:
                self.assertIn(evidence.document_id,source_ids)
        for revision in self.revisions:
            self.assertIn(revision.prior_document_id,source_ids)
            self.assertIn(revision.revision_document_id,source_ids)


if __name__=="__main__":
    unittest.main()
