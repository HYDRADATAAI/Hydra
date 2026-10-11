from __future__ import annotations

import io
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from hydra_constraint.polling import (
    BackoffPolicy,
    PollRunner,
    PollSpec,
    UrllibTransport,
    _NoRedirectHandler,
)


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


class PollPreflightTests(unittest.TestCase):
    class Cursors:
        def __init__(self):
            self.reads = 0

        def adapter(self, _source):
            self.reads += 1
            return {"cursor": None}

    class Transport:
        def __init__(self):
            self.calls = 0

        def fetch(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("invalid SEC spec must fail before transport")

    def test_sec_preflight_accepts_boundary_values_and_exempts_non_sec_specs(self):
        runner = PollRunner(None, None, None, None)
        runner.validate_live_spec(
            sec_spec(url="https://DATA.SEC.GOV.:443/submissions/CIK0000000001.json")
        )
        runner.validate_live_spec(
            PollSpec(
                name="fixture",
                adapter="fixture",
                source_class="fixture",
                url="https://example.test/feed",
                parser="json_records",
                cadence_minutes=60,
                stale_after_minutes=180,
                headers={},
                max_rps=0,
            )
        )

    def test_sec_preflight_rejects_invalid_selectors_urls_headers_and_rates(self):
        runner = PollRunner(None, None, None, None)
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
                runner.validate_live_spec(sec_spec(**changes))

    def test_poll_rejects_invalid_spec_before_cursor_transport_or_archive(self):
        class UnexpectedCall:
            def __getattr__(self, name):
                raise AssertionError(f"preflight must run before {name}")

        runner = PollRunner(
            UnexpectedCall(), UnexpectedCall(), UnexpectedCall(), UnexpectedCall()
        )
        with self.assertRaisesRegex(ValueError, "matching sec_edgar"):
            runner.poll(sec_spec(source_class="other"))

    def test_poll_rejects_unicode_dot_sec_alias_before_cursor_or_transport(self):
        for separator in ("\\u3002", "\\uff0e", "\\uff61"):
            with self.subTest(separator=separator):
                cursors = self.Cursors()
                transport = self.Transport()
                runner = PollRunner(None, cursors, None, transport)
                spec = PollSpec(
                    name="fixture",
                    adapter="fixture",
                    source_class="fixture",
                    url=f"https://data{separator}sec{separator}gov/feed",
                    parser="json_records",
                    cadence_minutes=60,
                    stale_after_minutes=180,
                    headers={},
                    max_rps=1,
                )

                with self.assertRaisesRegex(ValueError, "matching sec_edgar"):
                    runner.poll(spec)

                self.assertEqual(cursors.reads, 0)
                self.assertEqual(transport.calls, 0)

    def test_poll_rejects_over_limit_sec_rate_before_cursor_or_transport(self):
        cursors = self.Cursors()
        transport = self.Transport()
        runner = PollRunner(None, cursors, None, transport)

        with self.assertRaisesRegex(ValueError, "at or below 10"):
            runner.poll(sec_spec(max_rps=20))

        self.assertEqual(cursors.reads, 0)
        self.assertEqual(transport.calls, 0)

    def test_sec_user_agent_requires_a_contact_email(self):
        runner = PollRunner(None, None, None, None)
        with self.assertRaisesRegex(ValueError, "include a contact email"):
            runner.validate_live_spec(sec_spec(headers={"User-Agent": "Hydra Bot"}))

    def test_sec_polling_spaces_requests_at_configured_rate(self):
        class Cursors(self.Cursors):
            def mark_error(self, *_args, **_kwargs):
                pass

        class FailingTransport:
            def __init__(self):
                self.calls = 0

            def fetch(self, *_args, **_kwargs):
                self.calls += 1
                raise OSError("synthetic offline failure")

        class Sleeper:
            def __init__(self):
                self.delays = []

            def sleep(self, delay):
                self.delays.append(delay)

        cursors, transport, sleeper = Cursors(), FailingTransport(), Sleeper()
        runner = PollRunner(None, cursors, None, transport, sleeper=sleeper)
        spec = sec_spec(backoff=BackoffPolicy(max_attempts=1), max_rps=10)

        with patch("hydra_constraint.polling._SEC_LAST_REQUEST_AT", None), patch(
            "hydra_constraint.polling.time.monotonic",
            side_effect=[100.0, 100.0, 100.05, 100.1],
        ):
            runner.poll(spec)
            runner.poll(spec)

        self.assertEqual(transport.calls, 2)
        self.assertEqual(sleeper.delays, [0.05])

    def test_poll_rejects_placeholder_user_agent_before_cursor_or_transport(self):
        cursors = self.Cursors()
        transport = self.Transport()
        runner = PollRunner(None, cursors, None, transport)

        with self.assertRaisesRegex(ValueError, "non-empty, non-placeholder"):
            runner.poll(sec_spec(headers={"User-Agent": "REPLACE_ME"}))

        self.assertEqual(cursors.reads, 0)
        self.assertEqual(transport.calls, 0)


class NoRedirectTransportTests(unittest.TestCase):
    def test_handler_refuses_redirect_and_transport_installs_it(self):
        handler = _NoRedirectHandler()
        request = urllib.request.Request("https://www.sec.gov/data")
        self.assertIsNone(
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": "https://attacker.example/collect"},
                "https://attacker.example/collect",
            )
        )

        error = urllib.error.HTTPError(
            "https://www.sec.gov/data",
            302,
            "Found",
            {"Location": "https://attacker.example/collect"},
            io.BytesIO(b"redirect refused"),
        )

        class FakeOpener:
            def open(self, _request, timeout):
                self.assert_timeout = timeout
                raise error

        opener = FakeOpener()
        with patch(
            "hydra_constraint.polling.urllib.request.build_opener",
            return_value=opener,
        ) as build_opener:
            response = UrllibTransport().fetch(
                "https://www.sec.gov/data",
                headers={"User-Agent": "Hydra contact@example.test"},
            )

        self.assertIsInstance(build_opener.call_args.args[0], _NoRedirectHandler)
        self.assertEqual(response.status, 302)
        self.assertEqual(response.body, b"redirect refused")
        self.assertTrue(error.fp.closed)


if __name__ == "__main__":
    unittest.main()
