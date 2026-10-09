from __future__ import annotations

import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from function.app import lambda_handler
from function.processor import process_csv


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic_market_events.csv"


_CONTENT_LENGTH_UNSET = object()


class TrackingBody(io.BytesIO):
    def __init__(self, value: bytes):
        super().__init__(value)
        self.read_sizes: list[int] = []
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        chunk = super().read(size)
        self.bytes_read += len(chunk)
        return chunk


class FakeS3:
    def __init__(
        self,
        source: bytes,
        *,
        content_length: object = _CONTENT_LENGTH_UNSET,
        body: object | None = None,
    ):
        self.source = source
        self.content_length = content_length
        self.body = body if body is not None else io.BytesIO(source)
        self.get_calls: list[dict[str, object]] = []
        self.put_calls: list[dict[str, object]] = []

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        response = {"Body": self.body}
        if self.content_length is _CONTENT_LENGTH_UNSET:
            response["ContentLength"] = len(self.source)
        elif self.content_length is not None:
            response["ContentLength"] = self.content_length
        return response

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        return {"ETag": '"synthetic"'}


def s3_event(
    key: str = "raw/synthetic+market.csv", *, size: int | None = None
) -> dict[str, object]:
    object_data: dict[str, object] = {"key": key}
    if size is not None:
        object_data["size"] = size
    return {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "hydra-raw-example"},
                    "object": object_data,
                },
            }
        ]
    }


class LambdaHandlerTests(unittest.TestCase):
    def test_handler_writes_encrypted_deterministic_objects(self):
        source = FIXTURE.read_bytes()
        expected = process_csv(source)
        client = FakeS3(source)

        with patch.dict(os.environ, {"CURATED_BUCKET": "hydra-curated-example"}):
            result = lambda_handler(
                s3_event(size=len(source)), None, s3_client=client
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(client.get_calls[0]["Key"], "raw/synthetic market.csv")
        self.assertEqual(len(client.put_calls), 3)
        self.assertEqual(
            [call["Key"] for call in client.put_calls],
            [
                f"curated/accepted/{expected.run_id}/normalized_events.jsonl",
                f"curated/quarantine/{expected.run_id}/quarantine_records.jsonl",
                f"curated/manifests/{expected.run_id}/manifest.json",
            ],
        )
        self.assertTrue(client.put_calls[-1]["Key"].endswith("/manifest.json"))
        for call in client.put_calls:
            self.assertEqual(call["Bucket"], "hydra-curated-example")
            self.assertEqual(call["ServerSideEncryption"], "AES256")
            self.assertEqual(call["Metadata"]["pipeline-run-id"], expected.run_id)

    def test_replay_targets_the_same_keys_and_bytes(self):
        source = FIXTURE.read_bytes()
        first = FakeS3(source)
        second = FakeS3(source)

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            lambda_handler(
                s3_event(size=len(source)), None, s3_client=first
            )
            lambda_handler(
                s3_event(size=len(source)), None, s3_client=second
            )

        self.assertEqual(
            [(call["Key"], call["Body"]) for call in first.put_calls],
            [(call["Key"], call["Body"]) for call in second.put_calls],
        )

    def test_event_size_rejects_before_get_object(self):
        client = FakeS3(b"small")
        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated", "MAX_SOURCE_OBJECT_BYTES": "8"},
        ):
            with self.assertRaisesRegex(ValueError, "source object exceeds"):
                lambda_handler(s3_event(size=9), None, s3_client=client)

        self.assertEqual(client.get_calls, [])
        self.assertEqual(client.put_calls, [])

    def test_get_object_content_length_rejects_before_body_read(self):
        body = TrackingBody(b"unread body")
        client = FakeS3(b"", content_length=9, body=body)
        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated", "MAX_SOURCE_OBJECT_BYTES": "8"},
        ):
            with self.assertRaisesRegex(ValueError, "source object exceeds"):
                lambda_handler(s3_event(size=8), None, s3_client=client)

        self.assertEqual(len(client.get_calls), 1)
        self.assertEqual(body.read_sizes, [])
        self.assertTrue(body.closed)
        self.assertEqual(client.put_calls, [])

    def test_capped_body_read_rejects_when_size_metadata_is_missing(self):
        body = TrackingBody(b"123456789")
        client = FakeS3(b"", content_length=None, body=body)
        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated", "MAX_SOURCE_OBJECT_BYTES": "8"},
        ):
            with self.assertRaisesRegex(ValueError, "body exceeds max_bytes=8"):
                lambda_handler(s3_event(), None, s3_client=client)

        self.assertEqual(body.bytes_read, 9)
        self.assertTrue(body.closed)
        self.assertEqual(client.put_calls, [])

    def test_object_exactly_at_configured_limit_is_processed(self):
        source = FIXTURE.read_bytes()
        client = FakeS3(source)
        with patch.dict(
            os.environ,
            {
                "CURATED_BUCKET": "curated",
                "MAX_SOURCE_OBJECT_BYTES": str(len(source)),
            },
        ):
            result = lambda_handler(
                s3_event(size=len(source)), None, s3_client=client
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(client.put_calls), 3)

    def test_content_length_mismatch_fails_before_output_writes(self):
        source = FIXTURE.read_bytes()
        client = FakeS3(source, body=TrackingBody(source[:-1]))
        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated"},
        ):
            with self.assertRaisesRegex(ValueError, "body length does not match"):
                lambda_handler(
                    s3_event(size=len(source)), None, s3_client=client
                )

        self.assertEqual(client.put_calls, [])

    def test_non_s3_event_fails_closed(self):
        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            with self.assertRaisesRegex(ValueError, "no S3 ObjectCreated records"):
                lambda_handler({"Records": []}, None, s3_client=FakeS3(b""))

    def test_missing_output_bucket_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CURATED_BUCKET"):
                lambda_handler(s3_event(), None, s3_client=FakeS3(FIXTURE.read_bytes()))


if __name__ == "__main__":
    unittest.main()
