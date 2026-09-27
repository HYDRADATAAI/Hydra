"""Do not discard evidence caveats or accept extra authority claims."""
import copy
import unittest
from tests import test_first_slice_materialization as fixtures
from hydra_constraint_t1_raw.first_slice_materialization import FirstSliceMaterializationError, validate_public_materialization_attestation
from hydra_constraint_t1_raw.replay_lineage import build_replay_lineage_packet, validate_replay_lineage_packet, _packet_digest

class UnverifiedMetadataBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FirstSliceMaterializationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_capture_cannot_drop_unverified_timestamp_status(self):
        plan = copy.deepcopy(self.fixture.plan)
        plan['captures'][0]['acquisition_verification_status'] = 'TIMESTAMP_UNVERIFIED'
        with self.assertRaises(FirstSliceMaterializationError):
            self.fixture.run_plan(plan)
        self.assertFalse((self.fixture.private / 'receipts').exists())
        self.assertEqual('TIMESTAMP_UNVERIFIED', plan['captures'][0]['acquisition_verification_status'])

    def test_attestation_and_replay_builder_reject_unverified_member(self):
        attestation = self.fixture.run_plan()
        attestation['members'][0]['acquisition_verification_status'] = 'TIMESTAMP_UNVERIFIED'
        for operation in (validate_public_materialization_attestation, build_replay_lineage_packet):
            with self.subTest(operation=operation.__name__), self.assertRaises(FirstSliceMaterializationError):
                operation(attestation=attestation, registry=self.fixture.registry)

    def test_extra_authority_and_temporal_fields_cannot_cross_boundaries(self):
        good = self.fixture.run_plan()
        for field, value in [('known_at','2000-01-01T00:00:00Z'), ('canonical_admission',True),
                             ('production_active',True), ('timestamp_verified',True),
                             ('metadata',{'acquisition_status':'TIMESTAMP_UNVERIFIED'})]:
            for location in ('root','member'):
                bad=copy.deepcopy(good)
                (bad if location=='root' else bad['members'][0])[field]=value
                with self.subTest(field=field, location=location), self.assertRaises(FirstSliceMaterializationError):
                    validate_public_materialization_attestation(attestation=bad,registry=self.fixture.registry)

    def test_replay_packet_rejects_added_authority_even_with_recomputed_digest(self):
        good=build_replay_lineage_packet(attestation=self.fixture.run_plan(),registry=self.fixture.registry)
        for field,value in [('production_active',True), ('acquisition_verification_status','TIMESTAMP_UNVERIFIED')]:
            bad=copy.deepcopy(good);bad[field]=value;bad['packet_sha256']=_packet_digest(bad)
            with self.subTest(field=field), self.assertRaises(FirstSliceMaterializationError):
                validate_replay_lineage_packet(packet=bad,registry=self.fixture.registry)

if __name__=='__main__':unittest.main()
