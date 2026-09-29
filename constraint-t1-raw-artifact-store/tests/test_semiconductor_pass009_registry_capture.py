"""Exercise semiconductor orchestration with synthetic browser bodies, real T1 storage."""
from contextlib import nullcontext, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
if __package__:
    from .test_automated_browser_private_source_capture import capture, ROOT
else:
    from test_automated_browser_private_source_capture import capture, ROOT

SLICE = 'SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1'

class SemiconductorRegistryTests(unittest.TestCase):
    def registry(self):
        return {'slice_id': SLICE, 'sources': [dict(source_id=f'SRC-SYNTHETIC-{i}', url=f'https://example.com/document-{i}', expected_content_type='application/pdf') for i in range(20)]}

    def test_profile_rejects_wrong_slice_and_count(self):
        for field, value in [('slice_id', capture.EXPECTED_SLICE_ID), ('sources', self.registry()['sources'][:19])]:
            registry = self.registry()
            registry[field] = value
            with self.subTest(field=field), self.assertRaises(capture.CaptureError):
                capture.validate_registry(registry, slice_id=SLICE, source_count=20)

    def test_pass012_resumes_six_pass009_captures(self):
        folder = ROOT / 'docs/constraint/implementation'
        old = json.loads((folder / 'HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS009_CAPTURE_REGISTRY_20260926.json').read_text())
        new = json.loads((folder / 'HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS012_CAPTURE_REGISTRY_20260926.json').read_text())
        capture.validate_registry(new, slice_id=SLICE, source_count=20)
        self.assertEqual(old['sources'][:6], new['sources'][:6])
        self.assertEqual(old['sources'][7:], new['sources'][7:])
        changed = dict(new['sources'][6], url=old['sources'][6]['url'])
        self.assertEqual(changed, old['sources'][6])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = []
            for index, source in enumerate(old['sources'][:6]):
                body = b'<html>' + b'synthetic body ' * 100 + b'</html>'
                path = root / f'{index}.html'
                path.write_bytes(body)
                row = capture.CapturedDocument(source['source_id'], source['url'], 'SV-SYNTHETIC-' + str(index), capture.utc_timestamp(), 200, 'text/html', len(body), hashlib.sha256(body).hexdigest(), path, 'PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT', 'chrome', (source['url'],))
                entries.append(capture._capture_metadata(row))
            journal_path = root / 'journal.json'
            journal_path.write_text(json.dumps(dict(schema_version=capture.CAPTURE_JOURNAL_SCHEMA, slice_id=SLICE, authoritative=False, t1_release_written=False, capture_dir=str(root), entries=entries)))
            _, _, resumed = capture._load_resume_journal(journal_path=journal_path, sources=new['sources'], public_repo_root=ROOT, slice_id=SLICE)
            self.assertEqual(len(resumed), 6)

    def test_synthetic_capture_reaches_existing_materializer_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / 'HYDRA_SYNTHETIC_PASS009_REGISTRY.json'
            registry.write_text(json.dumps(self.registry()))
            args = capture.build_parser().parse_args(['--repo-root', str(ROOT), '--private-root', str(root / 'private'), '--semiconductor-registry', str(registry), '--authorized-public-acquisition', '--fresh'])
            def fake_capture(**kw):
                source = kw['source']
                body = b'%PDF-1.7\n' + source['source_id'].encode() * 100
                path = kw['capture_dir'] / (source['source_id'] + '.pdf')
                path.write_bytes(body)
                return capture.CapturedDocument(source['source_id'], source['url'], 'SV-' + source['source_id'], capture.utc_timestamp(), 200, 'application/pdf', len(body), hashlib.sha256(body).hexdigest(), path, 'PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT', 'chrome', (source['url'],))
            calls = []
            original_run = capture._run_checked
            def run_checked(command, **kwargs):
                calls.append(command)
                return original_run(command, **kwargs)
            fake_playwright = SimpleNamespace(sync_playwright=lambda: nullcontext(object()))
            with patch.dict('sys.modules', {'playwright': SimpleNamespace(), 'playwright.sync_api': fake_playwright}), patch.object(capture, '_launch_persistent_context', return_value=(SimpleNamespace(close=lambda: None), 'chrome')), patch.object(capture, 'capture_source', side_effect=fake_capture), patch.object(capture, '_run_checked', side_effect=run_checked), redirect_stdout(io.StringIO()):
                self.assertEqual(capture.run(args), 0)
            self.assertEqual(len(calls), 2)  # materialization and attestation validation
            self.assertEqual(len(list((root / 'private/raw/receipts').glob('*/*.json'))), 20)
            self.assertEqual(len(list((root / 'private/raw/releases').glob('*.json'))), 1)
            journals = list((root / 'private/metadata').glob('*SEMICONDUCTOR_PASS009*JOURNAL*'))
            self.assertEqual(len(journals), 1)
            journal = json.loads(journals[0].read_text())
            self.assertEqual(journal['slice_id'], SLICE)
            self.assertTrue(journal['t1_release_written'])
            self.assertNotIn('replay_lineage_path', journal)
            self.assertIsNone(capture._find_latest_incomplete_journal(root / 'private/metadata'))

if __name__ == '__main__': unittest.main()
