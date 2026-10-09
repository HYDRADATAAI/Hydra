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
    def __init__(self, source: bytes, operations=None, fail_on_put=None):
        self.source = source
        self.get_calls: list[dict[str, object]] = []
        self.put_calls: list[dict[str, object]] = []
        self.operations = operations if operations is not None else []
        self.fail_on_put = fail_on_put

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"Body": io.BytesIO(self.source)}

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.operations.append(("put", kwargs["Key"]))
        if self.fail_on_put == len(self.put_calls):
            raise RuntimeError("injected S3 failure")
        return {"ETag": '"synthetic"'}


class AlreadyExistsError(Exception):
    response = {"Error": {"Code": "AlreadyExistsException"}}


class FakeGlue:
    def __init__(self, operations=None, existing_partition=None):
        self.operations = operations if operations is not None else []
        self.partition_calls: list[dict[str, object]] = []
        self.existing_partition = existing_partition
        self.get_partition_calls: list[dict[str, object]] = []

    def create_partition(self, **kwargs):
        self.partition_calls.append(kwargs)
        self.operations.append(("partition", kwargs["PartitionInput"]["Values"][0]))
        if self.existing_partition is not None:
            raise AlreadyExistsError()
        self.existing_partition = kwargs["PartitionInput"]
        return {}

    def get_partition(self, **kwargs):
        self.get_partition_calls.append(kwargs)
        return {"Partition": self.existing_partition}


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
        operations = []
        client = FakeS3(source, operations)
        glue = FakeGlue(operations)

        with patch.dict(
            os.environ,
            {
                "CURATED_BUCKET": "hydra-curated-example",
                "DATA_CATALOG_DATABASE": "hydra_public_market_data",
            },
        ):
            result = lambda_handler(
                s3_event(), None, s3_client=client, glue_client=glue
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
        self.assertEqual(
            operations[-1], ("partition", expected.run_id)
        )
        self.assertEqual(len(glue.partition_calls), 1)
        partition = glue.partition_calls[0]
        self.assertEqual(partition["DatabaseName"], "hydra_public_market_data")
        self.assertEqual(partition["TableName"], "normalized_events")
        self.assertEqual(partition["PartitionInput"]["Values"], [expected.run_id])
        self.assertEqual(
            partition["PartitionInput"]["StorageDescriptor"]["Location"],
            f"s3://hydra-curated-example/curated/accepted/{expected.run_id}/",
        )
        self.assertEqual(
            [kind for kind, _ in operations],
            ["put", "put", "put", "partition"],
        )
        for call in client.put_calls:
            self.assertEqual(call["Bucket"], "hydra-curated-example")
            self.assertEqual(call["ServerSideEncryption"], "AES256")
            self.assertEqual(call["Metadata"]["pipeline-run-id"], expected.run_id)

    def test_replay_targets_the_same_keys_and_bytes(self):
        source = FIXTURE.read_bytes()
        first = FakeS3(source)
        second = FakeS3(source)
        first_glue = FakeGlue()
        second_glue = FakeGlue()

        with patch.dict(
            os.environ,
            {
                "CURATED_BUCKET": "curated",
                "DATA_CATALOG_DATABASE": "hydra_public_market_data",
            },
        ):
            lambda_handler(s3_event(), None, s3_client=first, glue_client=first_glue)
            lambda_handler(s3_event(), None, s3_client=second, glue_client=second_glue)

        self.assertEqual(
            [(call["Key"], call["Body"]) for call in first.put_calls],
            [(call["Key"], call["Body"]) for call in second.put_calls],
        )
        self.assertEqual(first_glue.partition_calls, second_glue.partition_calls)

    def test_duplicate_partition_is_accepted_only_for_exact_run_location(self):
        source = FIXTURE.read_bytes()
        expected = process_csv(source)
        expected_partition = {
            "Values": [expected.run_id],
            "StorageDescriptor": {
                "Location": (
                    f"s3://curated/curated/accepted/{expected.run_id}/"
                )
            },
        }

        with patch.dict(
            os.environ,
            {
                "CURATED_BUCKET": "curated",
                "DATA_CATALOG_DATABASE": "hydra_public_market_data",
            },
        ):
            matching_glue = FakeGlue(existing_partition=expected_partition)
            lambda_handler(
                s3_event(),
                None,
                s3_client=FakeS3(source),
                glue_client=matching_glue,
            )
            self.assertEqual(len(matching_glue.get_partition_calls), 1)

            mismatch = {
                "Values": [expected.run_id],
                "StorageDescriptor": {"Location": "s3://curated/wrong-prefix/"},
            }
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                lambda_handler(
                    s3_event(),
                    None,
                    s3_client=FakeS3(source),
                    glue_client=FakeGlue(existing_partition=mismatch),
                )

    def test_failed_artifact_write_never_registers_queryable_partition(self):
        source = FIXTURE.read_bytes()
        for failed_write in (1, 2, 3):
            with self.subTest(failed_write=failed_write):
                operations = []
                client = FakeS3(source, operations, fail_on_put=failed_write)
                glue = FakeGlue(operations)

                with patch.dict(
                    os.environ,
                    {
                        "CURATED_BUCKET": "curated",
                        "DATA_CATALOG_DATABASE": "hydra_public_market_data",
                    },
                ):
                    with self.assertRaisesRegex(RuntimeError, "injected S3 failure"):
                        lambda_handler(
                            s3_event(),
                            None,
                            s3_client=client,
                            glue_client=glue,
                        )

                self.assertEqual(glue.partition_calls, [])
                self.assertNotIn("partition", [kind for kind, _ in operations])

    def test_non_s3_event_fails_closed(self):
        with patch.dict(
            os.environ,
            {
                "CURATED_BUCKET": "curated",
                "DATA_CATALOG_DATABASE": "hydra_public_market_data",
            },
        ):
            with self.assertRaisesRegex(ValueError, "no S3 ObjectCreated records"):
                lambda_handler(
                    {"Records": []},
                    None,
                    s3_client=FakeS3(b""),
                    glue_client=FakeGlue(),
                )

    def test_missing_output_bucket_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CURATED_BUCKET"):
                lambda_handler(
                    s3_event(),
                    None,
                    s3_client=FakeS3(FIXTURE.read_bytes()),
                    glue_client=FakeGlue(),
                )


if __name__ == "__main__":
    unittest.main()
