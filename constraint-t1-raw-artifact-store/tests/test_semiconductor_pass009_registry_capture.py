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
