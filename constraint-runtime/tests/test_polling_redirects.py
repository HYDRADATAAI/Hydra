from __future__ import annotations

import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from hydra_constraint.polling import (
    BackoffPolicy,
    PollRunner,
    PollSpec,
    UrllibTransport,
    _NoRedirectHandler,
)


class PollingRedirectTests(unittest.TestCase):
    def test_source_url_rejected_before_network_for_http_missing_host_or_credentials(self):
        transport = UrllibTransport()
        invalid_urls = (
            "http://data.sec.gov/feed",
            "https://",
            "https://user:secret@data.sec.gov/feed",
            "https://@data.sec.gov/feed",
        )
        for url in invalid_urls:
            with self.subTest(url=url), patch(
                "hydra_constraint.polling.urllib.request.build_opener"
            ) as build_opener:
                with self.assertRaises(ValueError):
                    transport.fetch(url)
                build_opener.assert_not_called()

    def test_transport_installs_handler_that_refuses_redirects(self):
        class Response:
            status = 200
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def __init__(self):
                self.body = b"ok"

            def read(self, size=-1):
                chunk = self.body[:size]
                self.body = self.body[len(chunk):]
                return chunk

        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.return_value = Response()
            UrllibTransport().fetch("https://data.sec.gov/feed")

        handler = build_opener.call_args.args[0]
        self.assertIsInstance(handler, _NoRedirectHandler)
        request = Request("https://data.sec.gov/feed")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://other.example/feed"
            )
        )

    def test_polling_redirect_fails_and_preserves_cursor(self):
        class Cursors:
            def __init__(self):
                self.state = {"cursor": "old"}
                self.errors = []

            def adapter(self, _source):
                return self.state

            def mark_error(self, source, polled_at, error):
                self.errors.append((source, polled_at, error))

        class Archive:
            def __init__(self):
                self.calls = []

            def archive(self, source, response, attempt):
                self.calls.append((source, response.status, attempt))
                return "synthetic-hash"

        class Durable:
            def ingest_adapted(self, _record):
                raise AssertionError("redirect response must not be parsed or ingested")

        class Sleeper:
            def sleep(self, _delay):
                raise AssertionError("terminal redirect must not retry")

        cursors, archive = Cursors(), Archive()
        runner = PollRunner(
            Durable(), cursors, archive, UrllibTransport(), sleeper=Sleeper()
        )
        spec = PollSpec(
            name="fixture", adapter="json_records", source_class="fixture",
            url="https://example.test/feed", parser="json_records",
            cadence_minutes=60, stale_after_minutes=60,
            backoff=BackoffPolicy(max_attempts=3),
        )
        redirect = HTTPError(
            spec.url, 302, "Found",
            {"Location": "https://other.example/feed"},
            BytesIO(b"redirect body"),
        )

        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.side_effect = redirect
            report = runner.poll(spec, cursor_value="new")

        self.assertEqual(report.status, "FAILED")
        self.assertEqual(report.http_statuses, [302])
        self.assertEqual(report.cursor_before, "old")
        self.assertEqual(report.cursor_after, "old")
        self.assertEqual(archive.calls, [("fixture", 302, 1)])
        self.assertEqual(len(cursors.errors), 1)
        self.assertIsInstance(build_opener.call_args.args[0], _NoRedirectHandler)


if __name__ == "__main__":
    unittest.main()
