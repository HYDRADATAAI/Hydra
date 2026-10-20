from __future__ import annotations

import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from function.app import GLUE_PARTITION_COLUMNS, lambda_handler
from function.processor import process_csv


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic_market_events.csv"


_CONTENT_LENGTH_UNSET = object()


class TrackingBody(io.BytesIO):
    def __init__(self, value: bytes, *, max_chunk_size: int | None = None):
        super().__init__(value)
        self.max_chunk_size = max_chunk_size
        self.read_sizes: list[int] = []
        self.bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.max_chunk_size is not None and size >= 0:
            size = min(size, self.max_chunk_size)
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
        operations=None,
        fail_on_put=None,
    ):
        self.source = source
        self.content_length = content_length
        self.body = body if body is not None else io.BytesIO(source)
        self.get_calls: list[dict[str, object]] = []
        self.put_calls: list[dict[str, object]] = []
        self.operations = operations if operations is not None else []
        self.fail_on_put = fail_on_put

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


def s3_event(
    key: str = "raw/synthetic+market.csv",
    *,
    size: int | None = None,
    version_id: str | None = "version-1",
) -> dict[str, object]:
    object_data: dict[str, object] = {"key": key}
    if size is not None:
        object_data["size"] = size
    if version_id is not None:
        object_data["versionId"] = version_id
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
    def setUp(self):
        database = patch.dict(
            os.environ, {"DATA_CATALOG_DATABASE": "hydra_public_market_data"}
        )
        database.start()
        self.addCleanup(database.stop)
        glue_client = patch("function.app._boto3_glue_client", side_effect=FakeGlue)
        glue_client.start()
        self.addCleanup(glue_client.stop)

    def test_handler_writes_encrypted_deterministic_objects(self):
        source = FIXTURE.read_bytes()
        expected = process_csv(source)
        operations = []
        client = FakeS3(source, operations=operations)
        glue = FakeGlue(operations)

        with patch.dict(os.environ, {"CURATED_BUCKET": "hydra-curated-example"}):
            result = lambda_handler(
                s3_event(size=len(source)),
                None,
                s3_client=client,
                glue_client=glue,
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(client.get_calls[0]["Key"], "raw/synthetic market.csv")
        self.assertEqual(client.get_calls[0]["VersionId"], "version-1")
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
            [kind for kind, _ in operations], ["put", "put", "put", "partition"]
        )
        self.assertEqual(glue.partition_calls[0]["PartitionInput"]["Values"], [expected.run_id])
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

    def test_any_oversized_event_record_is_rejected_before_get_or_put(self):
        event = s3_event(size=5)
        event["Records"].append(
            {
                "eventName": "ObjectCreated:Put",
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "hydra-raw-example"},
                    "object": {
                        "key": "raw/oversized.csv",
                        "size": 9,
                        "versionId": "version-2",
                    },
                },
            }
        )
        client = FakeS3(b"small")

        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated", "MAX_SOURCE_OBJECT_BYTES": "8"},
        ):
            with self.assertRaisesRegex(ValueError, "source object exceeds"):
                lambda_handler(event, None, s3_client=client)

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
        body = TrackingBody(source, max_chunk_size=7)
        client = FakeS3(source, body=body)
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
        self.assertGreater(len(body.read_sizes), 1)
        self.assertTrue(body.closed)
        self.assertEqual(len(client.put_calls), 3)

    def test_event_size_content_length_mismatch_rejects_before_body_read(self):
        body = TrackingBody(b"unused")
        client = FakeS3(b"", content_length=6, body=body)
        with patch.dict(
            os.environ,
            {"CURATED_BUCKET": "curated", "MAX_SOURCE_OBJECT_BYTES": "8"},
        ):
            with self.assertRaisesRegex(
                ValueError, "event object size does not match"
            ):
                lambda_handler(s3_event(size=7), None, s3_client=client)

        self.assertEqual(len(client.get_calls), 1)
        self.assertEqual(body.read_sizes, [])
        self.assertTrue(body.closed)
        self.assertEqual(client.put_calls, [])

    def test_invalid_content_length_rejects_without_read_or_writes(self):
        for content_length in (-1, 1.5, "6"):
            with self.subTest(content_length=content_length):
                body = TrackingBody(b"unused")
                client = FakeS3(
                    b"", content_length=content_length, body=body
                )
                with patch.dict(
                    os.environ,
                    {
                        "CURATED_BUCKET": "curated",
                        "MAX_SOURCE_OBJECT_BYTES": "8",
                    },
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "ContentLength must be a non-negative integer",
                    ):
                        lambda_handler(s3_event(size=7), None, s3_client=client)

                self.assertEqual(len(client.get_calls), 1)
                self.assertEqual(body.read_sizes, [])
                self.assertTrue(body.closed)
                self.assertEqual(client.put_calls, [])

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

    def test_invalid_or_over_limit_cap_fails_before_get(self):
        for configured_limit in ("1.5", "2000001", "0"):
            with self.subTest(configured_limit=configured_limit):
                client = FakeS3(FIXTURE.read_bytes())
                with patch.dict(
                    os.environ,
                    {
                        "CURATED_BUCKET": "curated",
                        "MAX_SOURCE_OBJECT_BYTES": configured_limit,
                    },
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "MAX_SOURCE_OBJECT_BYTES"
                    ):
                        lambda_handler(
                            s3_event(size=len(FIXTURE.read_bytes())),
                            None,
                            s3_client=client,
                        )
                self.assertEqual(client.get_calls, [])
                self.assertEqual(client.put_calls, [])

    def test_missing_event_version_uses_current_object_compatibility_path(self):
        source = FIXTURE.read_bytes()
        client = FakeS3(source)
        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            lambda_handler(
                s3_event(size=len(source), version_id=None),
                None,
                s3_client=client,
            )

        self.assertNotIn("VersionId", client.get_calls[0])

    def test_duplicate_partition_is_accepted_only_for_exact_run_location(self):
        source = FIXTURE.read_bytes()
        expected = process_csv(source)
        expected_partition = {
            "Values": [expected.run_id],
            "StorageDescriptor": {
                "Columns": list(GLUE_PARTITION_COLUMNS),
                "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                "Location": f"s3://curated/curated/accepted/{expected.run_id}/",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                "SerdeInfo": {
                    "Parameters": {"ignore.malformed.jsons": "false"},
                    "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                },
            },
        }

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            matching_glue = FakeGlue(existing_partition=expected_partition)
            lambda_handler(
                s3_event(),
                None,
                s3_client=FakeS3(source),
                glue_client=matching_glue,
            )
            self.assertEqual(len(matching_glue.get_partition_calls), 1)

            malformed_descriptor = {
                "Values": [expected.run_id],
                "StorageDescriptor": {
                    **expected_partition["StorageDescriptor"],
                    "Columns": [{"Name": "symbol", "Type": "integer"}],
                },
            }
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                lambda_handler(
                    s3_event(),
                    None,
                    s3_client=FakeS3(source),
                    glue_client=FakeGlue(existing_partition=malformed_descriptor),
                )

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
                client = FakeS3(source, operations=operations, fail_on_put=failed_write)
                glue = FakeGlue(operations)

                with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
                    with self.assertRaisesRegex(RuntimeError, "injected S3 failure"):
                        lambda_handler(
                            s3_event(),
                            None,
                            s3_client=client,
                            glue_client=glue,
                        )

                self.assertEqual(glue.partition_calls, [])
                self.assertNotIn("partition", [kind for kind, _ in operations])

    def test_malformed_s3_object_created_record_rejects_valid_sibling_before_processing(self):
        source = FIXTURE.read_bytes()
        valid_record = s3_event(size=len(source))["Records"][0]
        base_record = {
            "eventName": "ObjectCreated:Put",
            "eventSource": "aws:s3",
        }
        malformed_payloads = [
            ("missing s3", {}),
            ("wrong-type s3", {"s3": []}),
            ("missing bucket", {"s3": {"object": {}}}),
            ("wrong-type bucket", {"s3": {"bucket": [], "object": {}}}),
            (
                "missing bucket name",
                {"s3": {"bucket": {}, "object": {}}},
            ),
            (
                "wrong-type bucket name",
                {"s3": {"bucket": {"name": 42}, "object": {}}},
            ),
            (
                "empty bucket name",
                {"s3": {"bucket": {"name": ""}, "object": {}}},
            ),
            (
                "whitespace bucket name",
                {"s3": {"bucket": {"name": "  "}, "object": {}}},
            ),
            (
                "missing object",
                {"s3": {"bucket": {"name": "raw-bucket"}}},
            ),
            (
                "wrong-type object",
                {"s3": {"bucket": {"name": "raw-bucket"}, "object": []}},
            ),
            (
                "missing key",
                {"s3": {"bucket": {"name": "raw-bucket"}, "object": {}}},
            ),
            (
                "wrong-type key",
                {
                    "s3": {
                        "bucket": {"name": "raw-bucket"},
                        "object": {"key": 42},
                    }
                },
            ),
            (
                "empty key",
                {
                    "s3": {
                        "bucket": {"name": "raw-bucket"},
                        "object": {"key": ""},
                    }
                },
            ),
        ]

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            for case_name, payload in malformed_payloads:
                with self.subTest(case=case_name):
                    malformed_record = {**base_record, **payload}
                    event = {"Records": [valid_record, malformed_record]}
                    client = FakeS3(source)
                    glue = FakeGlue()

                    with self.assertRaisesRegex(
                        ValueError, "S3 ObjectCreated record"
                    ):
                        lambda_handler(
                            event,
                            None,
                            s3_client=client,
                            glue_client=glue,
                        )

                    self.assertEqual(client.get_calls, [])
                    self.assertEqual(client.put_calls, [])
                    self.assertEqual(glue.partition_calls, [])

    def test_malformed_s3_event_name_rejects_valid_sibling_before_processing(self):
        source = FIXTURE.read_bytes()
        valid_record = s3_event(size=len(source))["Records"][0]
        malformed_records = [
            {"eventSource": "aws:s3"},
            {"eventSource": "aws:s3", "eventName": None},
            {"eventSource": "aws:s3", "eventName": 42},
            {"eventSource": "aws:s3", "eventName": ""},
            {"eventSource": "aws:s3", "eventName": "  "},
        ]

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            for malformed_record in malformed_records:
                with self.subTest(event_name=malformed_record.get("eventName")):
                    event = {"Records": [valid_record, malformed_record]}
                    client = FakeS3(source)
                    glue = FakeGlue()

                    with self.assertRaisesRegex(
                        ValueError, "S3 source record eventName"
                    ):
                        lambda_handler(
                            event,
                            None,
                            s3_client=client,
                            glue_client=glue,
                        )

                    self.assertEqual(client.get_calls, [])
                    self.assertEqual(client.put_calls, [])
                    self.assertEqual(glue.partition_calls, [])

    def test_unrelated_and_non_object_created_records_remain_ignored(self):
        source = FIXTURE.read_bytes()
        event = s3_event(size=len(source))
        event["Records"].extend(
            [
                {
                    "eventName": "ObjectCreated:Put",
                    "eventSource": "aws:sqs",
                    "s3": [],
                },
                {
                    "eventName": "ObjectRemoved:Delete",
                    "eventSource": "aws:s3",
                    "s3": [],
                },
            ]
        )
        client = FakeS3(source)
        glue = FakeGlue()

        with patch.dict(os.environ, {"CURATED_BUCKET": "curated"}):
            result = lambda_handler(
                event,
                None,
                s3_client=client,
                glue_client=glue,
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(client.get_calls), 1)
        self.assertEqual(len(client.put_calls), 3)
        self.assertEqual(len(glue.partition_calls), 1)

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
