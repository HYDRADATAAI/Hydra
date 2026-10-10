from __future__ import annotations

import io
import unittest
from unittest.mock import patch
import urllib.error

from hydra_constraint.polling import (
    BackoffPolicy,
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
        self.read_sizes = []
        self.offset = 0

    def read(self, size):
        self.read_sizes.append(size)
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class PollingResponseLimitTests(unittest.TestCase):
    def test_response_limits_reject_nonpositive_and_non_integer_values(self):
        for value in (0, -1, True, 1.5, "3"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    UrllibTransport(max_bytes=value)
                with self.assertRaises(ValueError):
                    PollRunner(None, None, None, object(), max_response_bytes=value)

    def test_success_response_reads_exact_limit_with_one_byte_probe(self):
        stream = ReadStream(b"abc")
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.return_value = stream
            response = UrllibTransport(max_bytes=3).fetch("https://example.test/feed")

        self.assertEqual(response.body, b"abc")
        self.assertEqual(stream.read_sizes, [4, 1])

    def test_oversized_success_response_raises_after_one_byte_probe(self):
        stream = ReadStream(b"abcd")
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.return_value = stream
            with self.assertRaises(ResponseTooLargeError):
                UrllibTransport(max_bytes=3).fetch("https://example.test/feed")

        self.assertEqual(stream.read_sizes, [4])

    def test_oversized_http_error_response_is_also_bounded(self):
        class TrackedErrorBody(io.BytesIO):
            bytes_read = 0

            def read(self, size=-1):
                chunk = super().read(size)
                self.bytes_read += len(chunk)
                return chunk

        body = TrackedErrorBody(b"abcd")
        error = urllib.error.HTTPError(
            "https://example.test/feed", 503, "unavailable", {}, body
        )
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.side_effect = error
            with self.assertRaises(ResponseTooLargeError):
                UrllibTransport(max_bytes=3).fetch("https://example.test/feed")

        self.assertEqual(body.bytes_read, 4)
        self.assertTrue(body.closed)

    def test_oversized_injected_response_fails_before_archive_and_parse(self):
        class Cursors:
            def __init__(self):
                self.errors = []

            def adapter(self, _source):
                return {"cursor": "old"}

            def mark_error(self, source, polled_at, error):
                self.errors.append((source, polled_at, error))

        class Transport:
            def __init__(self):
                self.calls = 0

            def fetch(self, _url, _headers):
                self.calls += 1
                return HttpResponse(
                    "https://example.test/feed", 200, {}, b'{"records":[]}',
                    "2026-10-09T00:00:00Z",
                )

        class Archive:
            def __init__(self):
                self.calls = 0

            def archive(self, *_args):
                self.calls += 1
                return "unused"

        class Durable:
            def ingest_adapted(self, _record):
                raise AssertionError("oversized response must not be parsed or ingested")

        class Sleeper:
            def __init__(self):
                self.delays = []

            def sleep(self, delay):
                self.delays.append(delay)

        cursors, transport, archive, sleeper = Cursors(), Transport(), Archive(), Sleeper()
        runner = PollRunner(
            Durable(), cursors, archive, transport, sleeper=sleeper,
            max_response_bytes=3,
        )
        spec = PollSpec(
            name="fixture", adapter="json_records", source_class="fixture",
            url="https://example.test/feed", parser="json_records",
            cadence_minutes=60, stale_after_minutes=60,
            backoff=BackoffPolicy(max_attempts=3),
        )

        report = runner.poll(spec, cursor_value="new")

        self.assertEqual(report.status, "FAILED")
        self.assertEqual(report.http_statuses, [200])
        self.assertEqual(report.cursor_before, "old")
        self.assertEqual(report.cursor_after, "old")
        self.assertEqual(transport.calls, 1)
        self.assertEqual(archive.calls, 0)
        self.assertEqual(sleeper.delays, [])
        self.assertEqual(len(cursors.errors), 1)


    def test_bounded_read_retries_short_reads_until_eof_or_limit(self):
        class ShortReadStream(ReadStream):
            def __init__(self, body, chunk_size):
                super().__init__(body)
                self.chunk_size = chunk_size
                self.offset = 0

            def read(self, size):
                self.read_sizes.append(size)
                chunk = self.body[self.offset:self.offset + min(size, self.chunk_size)]
                self.offset += len(chunk)
                return chunk

        stream = ShortReadStream(b"abcde", chunk_size=2)
        with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
            build_opener.return_value.open.return_value = stream
            response = UrllibTransport(max_bytes=5).fetch("https://example.test/feed")

        self.assertEqual(response.body, b"abcde")
        self.assertEqual(stream.read_sizes, [6, 4, 2, 1])

    def test_legacy_urllib_subclass_keeps_fetch_signature_and_post_fetch_cap(self):
        class LegacyTransport(UrllibTransport):
            def __init__(self):
                super().__init__(max_bytes=100)
                self.calls = 0

            def fetch(self, url, headers=None, timeout=20):
                self.calls += 1
                return HttpResponse(
                    url, 200, {}, b"abcd", "2026-10-09T00:00:00Z",
                )

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

            def archive(self, *args):
                self.calls.append(args)
                return "unused"

        class Durable:
            def ingest_adapted(self, _record):
                raise AssertionError("oversized response must not be ingested")

        class Sleeper:
            def sleep(self, _delay):
                raise AssertionError("oversized response must be terminal")

        transport, cursors, archive = LegacyTransport(), Cursors(), Archive()
        runner = PollRunner(
            Durable(), cursors, archive, transport, sleeper=Sleeper(),
            max_response_bytes=3,
        )
        spec = PollSpec(
            name="fixture", adapter="json_records", source_class="fixture",
            url="https://example.test/feed", parser="json_records",
            cadence_minutes=60, stale_after_minutes=60,
            backoff=BackoffPolicy(max_attempts=3),
        )

        report = runner.poll(spec, cursor_value="new")

        self.assertEqual(report.status, "FAILED")
        self.assertEqual(report.http_statuses, [200])
        self.assertEqual(report.cursor_before, "old")
        self.assertEqual(report.cursor_after, "old")
        self.assertEqual(transport.calls, 1)
        self.assertEqual(archive.calls, [])
        self.assertEqual(len(cursors.errors), 1)

    def test_invalid_builtin_transport_url_fails_before_cursor_access(self):
        class UnexpectedCall:
            def __getattr__(self, name):
                raise AssertionError(f"URL validation must precede {name}")

        runner = PollRunner(
            UnexpectedCall(), UnexpectedCall(), UnexpectedCall(), UrllibTransport()
        )
        spec = PollSpec(
            name="fixture", adapter="json_records", source_class="fixture",
            url="http://example.test/feed", parser="json_records",
            cadence_minutes=60, stale_after_minutes=60,
            backoff=BackoffPolicy(max_attempts=3),
        )

        with self.assertRaisesRegex(ValueError, "HTTPS"):
            runner.poll(spec)

    def test_oversized_builtin_success_and_error_fail_before_archive(self):
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

            def archive(self, *args):
                self.calls.append(args)
                return "unused"

        class Durable:
            def ingest_adapted(self, _record):
                raise AssertionError("oversized response must not be ingested")

        class Sleeper:
            def __init__(self):
                self.delays = []

            def sleep(self, delay):
                self.delays.append(delay)

        cases = (
            (200, ReadStream(b"abcd", status=200)),
            (
                503,
                urllib.error.HTTPError(
                    "https://example.test/feed", 503, "unavailable", {},
                    io.BytesIO(b"abcd"),
                ),
            ),
        )
        for status, response in cases:
            with self.subTest(status=status):
                cursors, archive, sleeper = Cursors(), Archive(), Sleeper()
                runner = PollRunner(
                    Durable(), cursors, archive, UrllibTransport(max_bytes=3),
                    sleeper=sleeper,
                )
                spec = PollSpec(
                    name="fixture", adapter="json_records", source_class="fixture",
                    url="https://example.test/feed", parser="json_records",
                    cadence_minutes=60, stale_after_minutes=60,
                    backoff=BackoffPolicy(max_attempts=3),
                )
                with patch("hydra_constraint.polling.urllib.request.build_opener") as build_opener:
                    if isinstance(response, Exception):
                        build_opener.return_value.open.side_effect = response
                    else:
                        build_opener.return_value.open.return_value = response
                    report = runner.poll(spec, cursor_value="new")

                self.assertEqual(report.status, "FAILED")
                self.assertEqual(report.http_statuses, [status])
                self.assertEqual(report.cursor_before, "old")
                self.assertEqual(report.cursor_after, "old")
                self.assertEqual(archive.calls, [])
                self.assertEqual(sleeper.delays, [])
                self.assertEqual(len(cursors.errors), 1)

if __name__ == "__main__":
    unittest.main()
