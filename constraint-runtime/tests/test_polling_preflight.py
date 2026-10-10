from __future__ import annotations

import unittest

from hydra_constraint.polling import PollRunner, PollSpec


def sec_spec(**changes):
    values = {
        "name": "sec",
        "adapter": "sec_edgar",
        "source_class": "sec_edgar",
        "url": "https://data.sec.gov/submissions/CIK0000000001.json",
        "parser": "sec_json",
        "cadence_minutes": 60,
        "stale_after_minutes": 180,
        "headers": {"uSeR-aGeNt": "Hydra test contact@example.test"},
        "max_rps": 10,
    }
    values.update(changes)
    return PollSpec(**values)


class PollingPreflightTests(unittest.TestCase):
    def setUp(self):
        self.runner = PollRunner(None, None, None, None)

    def test_sec_preflight_accepts_boundary_values_and_exempts_non_sec_specs(self):
        self.runner.validate_live_spec(sec_spec(
            url="https://DATA.SEC.GOV.:443/submissions/CIK0000000001.json",
        ))
        self.runner.validate_live_spec(PollSpec(
            name="fixture", adapter="fixture", source_class="fixture",
            url="https://example.test/feed", parser="json_records",
            cadence_minutes=60, stale_after_minutes=180,
            headers={}, max_rps=0,
        ))

    def test_sec_preflight_rejects_invalid_selectors_urls_headers_and_rates(self):
        invalid_specs = [
            {"adapter": "other"},
            {"source_class": "other"},
            {"parser": "json_records"},
            {"url": "http://data.sec.gov/feed"},
            {"url": "https://sec.gov.example.test/feed"},
            {"url": "https://user:secret@data.sec.gov/feed"},
            {"url": "https://data.sec.gov:444/feed"},
            {"url": "https://data.sec.gov:not-a-port/feed"},
            {"url": "https://["},
            {
                "adapter": "json_records",
                "source_class": "fixture",
                "parser": "json_records",
                "url": "https://data。sec.gov/feed",
            },
            {"headers": None},
            {"headers": {}},
            {"headers": {"User-Agent": "Hydra one", "user-agent": "Hydra two"}},
            {"headers": {"User-Agent": 5}},
            {"headers": {"User-Agent": "   "}},
            {"headers": {"User-Agent": "REPLACE_WITH_CONTACT"}},
            {"headers": {"User-Agent": "Hydra\ncontact@example.test"}},
            {"max_rps": True},
            {"max_rps": 0},
            {"max_rps": -1},
            {"max_rps": 10.01},
            {"max_rps": float("nan")},
            {"max_rps": float("inf")},
            {"max_rps": "fast"},
        ]
        for changes in invalid_specs:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.runner.validate_live_spec(sec_spec(**changes))

    def test_poll_rejects_invalid_sec_spec_before_cursor_transport_or_archive(self):
        class UnexpectedCall:
            def __getattr__(self, name):
                raise AssertionError(f"preflight must run before {name}")

        runner = PollRunner(
            UnexpectedCall(), UnexpectedCall(), UnexpectedCall(), UnexpectedCall()
        )
        with self.assertRaisesRegex(ValueError, "matching sec_edgar"):
            runner.poll(sec_spec(source_class="other"))


if __name__ == "__main__":
    unittest.main()
