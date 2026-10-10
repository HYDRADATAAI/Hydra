from __future__ import annotations

import unittest

from hydra_constraint.adapters import BISFederalRegisterAdapter
from hydra_constraint.event_stream import EventNormalizer


class AdapterTimestampTests(unittest.TestCase):
    def test_negative_offset_source_date_normalizes_to_utc(self):
        record = {
            "document_number": "2026-12345",
            "publication_date": "2026-10-10T12:00:00-05:00",
            "title": "Synthetic export-control notice",
            "target": "MAT_GALLIUM",
            "captured_at": "2026-10-10T13:00:00Z",
            "url": "https://example.invalid/notice",
        }
        adapted = BISFederalRegisterAdapter().adapt(record)

        self.assertEqual(adapted["occurred_at"], "2026-10-10T12:00:00-05:00")
        graph = {"nodes": [{"node_id": "MAT_GALLIUM", "name": "Gallium", "jurisdiction": "Global"}]}
        event = EventNormalizer(graph).normalize(adapted)
        self.assertEqual(event.occurred_at, "2026-10-10T17:00:00Z")
        self.assertEqual(event.known_at, "2026-10-10T17:00:00Z")


if __name__ == "__main__":
    unittest.main()