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


class FakeS3:
    def __init__(self, source: bytes):
        self.source = source
        self.get_calls: list[dict[str, object]] = []
        self.put_calls: list[dict[str, object]] = []

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"Body": io.BytesIO(self.source)}

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        return {"ETag": '"synthetic"'}


def s3_event(key: str = "raw/synthetic+market.csv") -> dict[str, object]:
    return {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "hydra-raw-example"},
                    "object": {"key": key},
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
            result = lambda_handler(s3_event(), None, s3_client=client)

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
            self.assertEqual(
                call["Metadata"]["transform-version"],
                "hydra-aws-market-normalizer-v2",
            )

    def test_replay_targets_the_same_keys_and_bytes(self):
        source = FIXTURE.read_bytes()
        first = FakeS3(source)
        second = FakeS3(source)

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            lambda_handler(s3_event(), None, s3_client=first)
            lambda_handler(s3_event(), None, s3_client=second)

        self.assertEqual(
            [(call["Key"], call["Body"]) for call in first.put_calls],
            [(call["Key"], call["Body"]) for call in second.put_calls],
        )

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
