import tempfile
import unittest
from pathlib import Path
from hydra_constraint_t1_raw import RawArtifactStore, is_ordinary_t2_eligible

class TimestampGateTests(unittest.TestCase):
    def test_imported_timestamps_never_establish_verification(self):
        for stamp in ('2000-01-01T00:00:00Z', '2026-09-27T12:00:00Z', '2099-01-01T00:00:00Z'):
            with self.subTest(stamp=stamp), tempfile.TemporaryDirectory() as temp:
                store = RawArtifactStore(Path(temp))
                receipt = store.persist(raw_bytes=b'synthetic only', source_id='SYNTHETIC',
                    source_version_id='V1', content_type='text/plain', acquired_at=stamp,
                    available_at=stamp, source_locator='synthetic://timestamp-test')
                manifest = store.write_release_manifest(release_id='TEST', created_at=stamp, receipts=[receipt])
                self.assertEqual((), store.validate_receipt(receipt))
                self.assertEqual((), store.validate_stored_release_manifest(manifest))
                self.assertFalse(is_ordinary_t2_eligible(receipt=receipt, release_manifest=manifest, store=store))
                for field, value in [('timestamp_verified', True), ('verification_status', 'VERIFIED'),
                                     ('attestor', 'self-declared'), ('known_at', stamp)]:
                    forged = dict(receipt, **{field: value})
                    self.assertFalse(is_ordinary_t2_eligible(receipt=forged, release_manifest=manifest, store=store))

if __name__ == '__main__':
    unittest.main()
