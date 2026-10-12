from __future__ import annotations

import io
import unittest
import urllib.error
from unittest.mock import patch

from hydra_constraint.polling import (
    HttpResponse,
    PollRunner,
    PollSpec,
    ResponseTooLargeError,
    UrllibTransport,
)


class ReadStream:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.headers = {}
        self.offset = 0
        self.read_sizes = []
        self.closed = False

    def read(self, size):
        self.read_sizes.append(size)
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True
        return False


class PollingResponseLimitTests(unittest.TestCase):
    def test_transport_rejects_invalid_limits(self):
        for value in (0, -1, True, 1.5, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                UrllibTransport(max_bytes=value)

    def test_success_body_is_read_only_to_cap_plus_one_and_stream_closes(self):
        stream = ReadStream(b"oversized")
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build:
            build.return_value.open.return_value = stream
            with self.assertRaises(ResponseTooLargeError):
                UrllibTransport(max_bytes=3).fetch("https://example.test/feed")

        self.assertEqual(stream.read_sizes, [4])
        self.assertTrue(stream.closed)

    def test_error_body_is_read_only_to_cap_plus_one_and_stream_closes(self):
        error = urllib.error.HTTPError(
            "https://example.test/feed", 503, "unavailable", {}, io.BytesIO(b"oversized")
        )
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build:
            build.return_value.open.side_effect = error
            with self.assertRaises(ResponseTooLargeError):
                UrllibTransport(max_bytes=3).fetch("https://example.test/feed")

        self.assertTrue(error.fp.closed)

    def test_injected_oversize_fails_before_archive_and_keeps_cursor(self):
        class Cursors:
            def __init__(self):
                self.state = {"cursor": "old"}
                self.errors = []

            def adapter(self, _source):
                return self.state

            def mark_error(self, source, polled_at, error):
                self.errors.append((source, polled_at, error))

        class Transport:
            def fetch(self, url, _headers):
                return HttpResponse(url, 200, {}, b"1234", "2026-10-11T00:00:00Z")

        class Archive:
            def __init__(self):
                self.calls = 0

            def archive(self, *_args):
                self.calls += 1

        class Durable:
            def ingest_adapted(self, _record):
                raise AssertionError("oversized response must not be ingested")

        cursors, archive = Cursors(), Archive()
        runner = PollRunner(
            Durable(), cursors, archive, Transport(), max_response_bytes=3
        )
        spec = PollSpec(
            name="fixture",
            adapter="json_records",
            source_class="fixture",
            url="https://example.test/feed",
            parser="json_records",
            cadence_minutes=60,
            stale_after_minutes=60,
        )

        report = runner.poll(spec, cursor_value="new")

        self.assertEqual(report.status, "FAILED")
        self.assertEqual(report.http_statuses, [200])
        self.assertEqual(report.cursor_before, "old")
        self.assertEqual(report.cursor_after, "old")
        self.assertEqual(archive.calls, 0)
        self.assertEqual(len(cursors.errors), 1)

    def test_builtin_transport_rejects_http_before_cursor_access(self):
        class UnexpectedCall:
            def __getattr__(self, name):
                raise AssertionError(f"HTTPS validation must precede {name}")

        runner = PollRunner(
            UnexpectedCall(), UnexpectedCall(), UnexpectedCall(), UrllibTransport()
        )
        spec = PollSpec(
            name="fixture",
            adapter="json_records",
            source_class="fixture",
            url="http://example.test/feed",
            parser="json_records",
            cadence_minutes=60,
            stale_after_minutes=60,
        )

        with self.assertRaisesRegex(ValueError, "HTTPS"):
            runner.poll(spec)


if __name__ == "__main__":
    unittest.main()
