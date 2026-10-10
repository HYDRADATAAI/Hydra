from __future__ import annotations

import unittest

from hydra_constraint.adapters import BISFederalRegisterAdapter
from hydra_constraint.event_stream import EventNormalizer, IngestError


class AdapterTimestampTests(unittest.TestCase):
    def normalize_publication_date(self, publication_date):
        record = {
            "document_number": "2026-12345",
            "publication_date": publication_date,
            "title": "Synthetic export-control notice",
            "target": "MAT_GALLIUM",
            "captured_at": "2026-10-10T13:00:00Z",
            "url": "https://example.invalid/notice",
        }
        adapted = BISFederalRegisterAdapter().adapt(record)
        graph = {"nodes": [{"node_id": "MAT_GALLIUM", "name": "Gallium", "jurisdiction": "Global"}]}
        return adapted, EventNormalizer(graph).normalize(adapted)

    def test_negative_offset_source_date_normalizes_to_utc(self):
        adapted, event = self.normalize_publication_date("2026-10-10T12:00:00-05:00")
        self.assertEqual(adapted["occurred_at"], "2026-10-10T12:00:00-05:00")
        self.assertEqual(event.occurred_at, "2026-10-10T17:00:00Z")
        self.assertEqual(event.known_at, "2026-10-10T17:00:00Z")

    def test_positive_offset_source_date_normalizes_to_utc(self):
        adapted, event = self.normalize_publication_date("2026-10-10T12:00:00+05:30")
        self.assertEqual(adapted["occurred_at"], "2026-10-10T12:00:00+05:30")
        self.assertEqual(event.occurred_at, "2026-10-10T06:30:00Z")

    def test_naive_source_date_defaults_to_utc(self):
        adapted, event = self.normalize_publication_date("2026-10-10T12:00:00")
        self.assertEqual(adapted["occurred_at"], "2026-10-10T12:00:00Z")
        self.assertEqual(event.occurred_at, "2026-10-10T12:00:00Z")

    def test_malformed_source_date_fails_normalization(self):
        record = {
            "document_number": "2026-12345",
            "publication_date": "2026-10-10Tnot-a-date",
            "title": "Synthetic export-control notice",
            "target": "MAT_GALLIUM",
            "captured_at": "2026-10-10T13:00:00Z",
            "url": "https://example.invalid/notice",
        }
        adapted = BISFederalRegisterAdapter().adapt(record)
        graph = {"nodes": [{"node_id": "MAT_GALLIUM", "name": "Gallium", "jurisdiction": "Global"}]}
        with self.assertRaises(IngestError):
            EventNormalizer(graph).normalize(adapted)


if __name__ == "__main__":
    unittest.main()