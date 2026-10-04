from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint.canary import (
    CanaryResponse,
    CanaryRunner,
    CanarySpec,
    load_specs,
)


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def fetch(self, spec, user_agent):
        self.calls.append((spec.name, user_agent))
        value = self.responses[spec.name]
        if isinstance(value, Exception):
            raise value
        return value


class LiveCanaryTests(unittest.TestCase):
    def test_marker_success(self):
        transport = FakeTransport({
            "bis": CanaryResponse(
                200,
                "https://example.test/bis",
                {"content-type": "text/html"},
                b"Federal Register Notices ... Export as CSV",
            )
        })
        result = CanaryRunner(transport).run_one(
            CanarySpec("bis", "https://example.test/bis", ["Federal Register Notices", "Export as CSV"])
        )
        self.assertEqual(result.status, "PASS")
        self.assertTrue(result.sha256)

    def test_missing_marker_fails(self):
        transport = FakeTransport({
            "ofac": CanaryResponse(200, "https://example.test/ofac", {}, b"Recent Actions")
        })
        result = CanaryRunner(transport).run_one(
            CanarySpec("ofac", "https://example.test/ofac", ["Recent Actions", "Sanctions List Updates"])
        )
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.missing_markers, ["Sanctions List Updates"])

    def test_http_failure_fails(self):
        transport = FakeTransport({
            "port": CanaryResponse(503, "https://example.test/port", {}, b"maintenance")
        })
        result = CanaryRunner(transport).run_one(
            CanarySpec("port", "https://example.test/port", ["Port of Los Angeles"])
        )
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.http_status, 503)

    def test_disabled_source_is_never_fetched(self):
        transport = FakeTransport({})
        result = CanaryRunner(transport).run_one(
            CanarySpec("sec", "https://data.sec.gov/test", [], enabled=False)
        )
        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(transport.calls, [])

    def test_empty_enabled_set_fails_closed(self):
        transport = FakeTransport({})
        report = CanaryRunner(transport).run([])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["enabled_sources"], 0)
        self.assertEqual(report["passed_sources"], 0)
        self.assertEqual(transport.calls, [])



    def test_report_is_read_only(self):
        transport = FakeTransport({
            "a": CanaryResponse(200, "https://example.test/a", {}, b"marker")
        })
        report = CanaryRunner(transport).run([
            CanarySpec("a", "https://example.test/a", ["marker"])
        ])
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["read_only"])
        self.assertFalse(report["ledger_mutation"])
        self.assertFalse(report["automatic_trading_action"])

    def test_config_must_be_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text(json.dumps({
                "read_only": False,
                "ledger_mutation": False,
                "sources": [],
            }))
            with self.assertRaises(ValueError):
                load_specs(p)


    def test_config_requires_automatic_trading_disabled(self):
        invalid_configs = [
            {"read_only": True, "ledger_mutation": False, "sources": []},
            {
                "read_only": True,
                "ledger_mutation": False,
                "automatic_trading_action": True,
                "sources": [],
            },
        ]
        for payload in invalid_configs:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as td:
                    p = Path(td) / "config.json"
                    p.write_text(json.dumps(payload))
                    with self.assertRaisesRegex(
                        ValueError, "automatic_trading_action=false"
                    ):
                        load_specs(p)

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.json"
            p.write_text(json.dumps({
                "read_only": True,
                "ledger_mutation": False,
                "automatic_trading_action": False,
                "sources": [],
            }))
            self.assertEqual(load_specs(p), [])


if __name__ == "__main__":
    unittest.main()
