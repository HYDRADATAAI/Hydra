"""Synthetic private-store integration tests; no real source capture claims."""
import json
from pathlib import Path
import tempfile
import unittest
from hydra_constraint_semiconductor_pass006_capture_intake import RawArtifactStore, intake, sources

class IntakeTests(unittest.TestCase):
    def test_persisted_release_and_fail_closed_boundaries(self):
        for mutation in ('none', 'missing', 'unknown', 'wrong_source', 'wrong_locator', 'quarantine', 'backdated', 'future', 'tampered_bytes', 'missing_receipt', 'traversal', 'symlink'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                store = RawArtifactStore(root=root / 'private', public_repo_root=root / 'public')
                mapping = {}
                receipts = []
                for i, (sid, source) in enumerate(sources().items()):
                    receipt = store.persist(raw_bytes=f'SYNTHETIC ONLY {i}'.encode(), source_id=sid,
                        source_version_id=f'SV-SYNTHETIC-{i}', content_type='text/plain',
                        source_locator='wrong' if i == 0 and mutation == 'wrong_locator' else source['url'],
                        acquired_at='2026-09-26T22:00:00Z',
                        available_at='2026-09-25T22:00:00Z' if i == 0 and mutation == 'backdated' else '2026-09-26T22:00:00Z',
                        processing_disposition='QUARANTINED' if i == 0 and mutation == 'quarantine' else 'ELIGIBLE')
                    mapping[sid] = f'receipts/{sid}/SV-SYNTHETIC-{i}.json'
                    receipts.append(receipt)
                keys = list(mapping)
                if mutation == 'missing': del mapping[keys[0]]
                if mutation == 'unknown': mapping['SRC-UNKNOWN'] = mapping[keys[0]]
                if mutation == 'wrong_source': mapping[keys[0]] = mapping[keys[1]]
                if mutation == 'tampered_bytes': (store.root / receipts[0]['artifact_relpath']).write_bytes(b'tampered')
                if mutation == 'missing_receipt': (store.root / mapping[keys[0]]).unlink()
                if mutation == 'traversal': mapping[keys[0]] = '../outside.json'
                if mutation == 'symlink':
                    outside = root / 'outside.json'
                    outside.write_text(json.dumps(receipts[0]))
                    (store.root / 'escape.json').symlink_to(outside)
                    mapping[keys[0]] = 'escape.json'
                when = '2026-09-26T21:00:00Z' if mutation == 'future' else '2026-09-26T23:00:00Z'
                if mutation == 'none':
                    result = intake(store, mapping, release_id='SYNTHETIC-PASS006', created_at=when)
                    self.assertEqual(len(result['members']), 10)
                    self.assertEqual(store.validate_stored_release_manifest(result), ())
                else:
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        intake(store, mapping, release_id='SYNTHETIC-PASS006', created_at=when)
                    self.assertFalse((store.root / 'releases/SYNTHETIC-PASS006.json').exists())

if __name__ == '__main__': unittest.main()
