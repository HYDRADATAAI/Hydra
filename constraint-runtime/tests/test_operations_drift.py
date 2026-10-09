from __future__ import annotations

import json
import unittest

from hydra_constraint import DriftGuard


class DriftGuardRecordTests(unittest.TestCase):
    def setUp(self):
        self.guard = DriftGuard({
            "source": {"required_record_keys": ["id", "value"]},
        })

    def test_later_record_missing_required_key_freezes(self):
        body = json.dumps({
            "records": [
                {"id": "first", "value": "present"},
                {"id": "second"},
            ],
        }).encode("utf-8")

        result = self.guard.inspect("source", "json_records", body)

        self.assertEqual(result.status, "FROZEN")
        self.assertIn("missing_record:value", result.issues)

    def test_later_non_object_record_freezes(self):
        body = json.dumps({
            "records": [
                {"id": "first", "value": "present"},
                None,
            ],
        }).encode("utf-8")

        result = self.guard.inspect("source", "json_records", body)

        self.assertEqual(result.status, "FROZEN")
        self.assertIn("invalid_record:1", result.issues)


if __name__ == "__main__":
    unittest.main()
