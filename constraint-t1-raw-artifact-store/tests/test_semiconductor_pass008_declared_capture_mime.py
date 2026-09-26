"""Extensionless PDF regression; only synthetic response bytes are used."""
import hashlib
from pathlib import Path
import tempfile
import unittest
if __package__:
    from .test_automated_browser_private_source_capture import capture, nine_sources, registry
else:
    from test_automated_browser_private_source_capture import capture, nine_sources, registry

URL = 'https://example.com/static-files/extensionless-document'
PDF = b'%PDF-1.7\n' + b'0' * 1100

class DeclaredMimeTests(unittest.TestCase):
    def validate(self, **changes):
        args = dict(source_id='SRC-MIME-TEST', exact_locator=URL, response_url=URL,
                    redirect_chain=[URL], status=200, observed_content_type='application/pdf',
                    body=PDF, declared_content_type='application/pdf')
        args.update(changes)
        return capture.validate_main_document(**args)

    def test_extensionless_pdf_accepted_with_explicit_declaration(self):
        self.assertEqual(self.validate(), 'application/pdf')

    def test_legacy_inference_is_unchanged(self):
        self.assertEqual(capture.expected_content_type(URL), 'text/html')
        self.assertEqual(capture.expected_content_type(URL + '.pdf'), 'application/pdf')
        with self.assertRaises(capture.CaptureError): self.validate(declared_content_type=None)

    def test_response_integrity_remains_required(self):
        for change in ({'body': b'x' * 1200}, {'body': b'%PDF-'},
                       {'observed_content_type': 'text/html'}, {'status': 403},
                       {'response_url': URL + '/redirect'}, {'redirect_chain': [URL, URL + '/redirect']}):
            with self.subTest(change=change), self.assertRaises(capture.CaptureError):
                self.validate(**change)

    def test_registry_declarations_fail_closed(self):
        for invalid in ('application/octet-stream', '', ['application/pdf'], 3):
            rows = nine_sources()
            rows[0]['expected_content_type'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(capture.CaptureError):
                capture.validate_registry(registry(rows))

    def test_resume_uses_registry_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / 'synthetic.pdf'
            body.write_bytes(PDF)
            source = dict(source_id='SRC-MIME-TEST', url=URL, expected_content_type='application/pdf')
            entry = dict(source_id=source['source_id'], source_locator=URL, http_status=200,
                         content_type='application/pdf', redirect_chain=[URL], source_version_id='SV-SYNTHETIC',
                         acquired_at='2026-09-26T21:00:00Z', artifact_sha256=hashlib.sha256(PDF).hexdigest(),
                         byte_length=len(PDF), body_path=str(body), capture_method='PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT',
                         browser_channel='chrome')
            result = capture._resume_entry_to_capture(entry=entry, source=source, public_repo_root=root / 'repo')
            self.assertEqual(result.content_type, 'application/pdf')
            source['expected_content_type'] = 'text/html'
            with self.assertRaises(capture.CaptureError):
                capture._resume_entry_to_capture(entry=entry, source=source, public_repo_root=root / 'repo')
