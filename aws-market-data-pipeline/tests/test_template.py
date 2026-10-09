from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = json.loads((ROOT / "template.json").read_text(encoding="utf-8"))


class TemplateContractTests(unittest.TestCase):
    def test_vertical_slice_resources_exist(self):
        resources = TEMPLATE["Resources"]
        expected_types = {
            "RawBucket": "AWS::S3::Bucket",
            "CuratedBucket": "AWS::S3::Bucket",
            "TransformFunction": "AWS::Serverless::Function",
            "DataCatalogDatabase": "AWS::Glue::Database",
            "NormalizedEventsTable": "AWS::Glue::Table",
            "ManifestTable": "AWS::Glue::Table",
            "AthenaWorkGroup": "AWS::Athena::WorkGroup",
        }
        self.assertEqual(
            {name: resources[name]["Type"] for name in expected_types},
            expected_types,
        )

    def test_buckets_are_private_encrypted_versioned_and_expiring(self):
        parameter_by_bucket = {
            "RawBucket": "RawBucketName",
            "CuratedBucket": "CuratedBucketName",
        }
        for name, parameter_name in parameter_by_bucket.items():
            properties = TEMPLATE["Resources"][name]["Properties"]
            self.assertEqual(properties["BucketName"], {"Ref": parameter_name})
            public = properties["PublicAccessBlockConfiguration"]
            self.assertTrue(all(public.values()))
            encryption = properties["BucketEncryption"]
            algorithm = encryption["ServerSideEncryptionConfiguration"][0][
                "ServerSideEncryptionByDefault"
            ]["SSEAlgorithm"]
            self.assertEqual(algorithm, "AES256")
            self.assertEqual(properties["VersioningConfiguration"]["Status"], "Enabled")
            self.assertEqual(
                properties["LifecycleConfiguration"]["Rules"][0]["Status"],
                "Enabled",
            )
            self.assertEqual(
                properties["LifecycleConfiguration"]["Rules"][0][
                    "NoncurrentVersionExpiration"
                ],
                {"NoncurrentDays": {"Ref": "ArtifactRetentionDays"}},
            )

    def test_bucket_name_parameters_break_the_s3_notification_cycle(self):
        for parameter_name in ("RawBucketName", "CuratedBucketName"):
            self.assertEqual(
                TEMPLATE["Parameters"][parameter_name]["AllowedPattern"],
                "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$",
            )

        policies = TEMPLATE["Resources"]["TransformFunction"]["Properties"][
            "Policies"
        ]
        serialized = json.dumps(policies, sort_keys=True)
        self.assertNotIn("RawBucket.Arn", serialized)
        self.assertNotIn("CuratedBucket.Arn", serialized)
        self.assertIn("${RawBucketName}/raw/*", serialized)
        self.assertIn("${CuratedBucketName}/curated/*", serialized)

    def test_glue_database_name_is_athena_compatible_and_configurable(self):
        parameter = TEMPLATE["Parameters"]["DataCatalogDatabaseName"]
        self.assertEqual(parameter["AllowedPattern"], "^[a-z0-9_]+$")
        self.assertEqual(
            TEMPLATE["Resources"]["DataCatalogDatabase"]["Properties"][
                "DatabaseInput"
            ]["Name"],
            {"Ref": "DataCatalogDatabaseName"},
        )

    def test_lambda_is_bounded_and_least_privilege(self):
        function = TEMPLATE["Resources"]["TransformFunction"]["Properties"]
        self.assertEqual(function["Runtime"], "python3.11")
        self.assertEqual(function["MemorySize"], 128)
        self.assertEqual(function["Timeout"], 30)
        self.assertEqual(function["ReservedConcurrentExecutions"], 2)
        statements = function["Policies"][0]["Statement"]
        actions = {action for statement in statements for action in statement["Action"]}
        self.assertEqual(actions, {"s3:GetObject", "s3:PutObject"})
        serialized = json.dumps(statements, sort_keys=True)
        self.assertNotIn('"Resource": "*"', serialized)

        event = function["Events"]["RawCsvUpload"]["Properties"]
        rules = event["Filter"]["S3Key"]["Rules"]
        self.assertEqual(
            rules,
            [
                {"Name": "prefix", "Value": "raw/"},
                {"Name": "suffix", "Value": ".csv"},
            ],
        )

    def test_manifest_table_and_consumer_view_gate_partial_publication(self):
        table = TEMPLATE["Resources"]["ManifestTable"]["Properties"]["TableInput"]
        self.assertEqual(table["Name"], "run_manifests")
        location = table["StorageDescriptor"]["Location"]["Fn::Sub"]
        self.assertTrue(location.endswith("/curated/manifests/"))
        columns = {column["Name"]: column["Type"] for column in table["StorageDescriptor"]["Columns"]}
        self.assertEqual(columns["outputs"], "map<string,struct<sha256:string>>")
        self.assertEqual(columns["pipeline_run_id"], "string")
        serde = table["StorageDescriptor"]["SerdeInfo"]
        self.assertEqual(
            serde["SerializationLibrary"],
            "org.apache.hive.hcatalog.data.JsonSerDe",
        )
        self.assertEqual(serde["Parameters"]["ignore.malformed.jsons"], "false")

        sql_path = ROOT / "sql" / "create_committed_normalized_events.sql"
        sql = sql_path.read_text(encoding="utf-8")
        self.assertIn("JOIN run_manifests", sql)
        self.assertIn("n.pipeline_run_id = m.pipeline_run_id", sql)
        self.assertIn("m.outputs['normalized_events.jsonl'].sha256 IS NOT NULL", sql)
        workflow = (ROOT.parent / ".github" / "workflows" / "aws-market-data-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("sql/create_committed_normalized_events.sql", workflow)
        self.assertIn("FROM committed_normalized_events", workflow)

    def test_glue_reads_only_accepted_prefix_and_athena_is_bounded(self):
        table = TEMPLATE["Resources"]["NormalizedEventsTable"]["Properties"]
        location = table["TableInput"]["StorageDescriptor"]["Location"]["Fn::Sub"]
        self.assertTrue(location.endswith("/curated/accepted/"))

        workgroup = TEMPLATE["Resources"]["AthenaWorkGroup"]["Properties"]
        config = workgroup["WorkGroupConfiguration"]
        self.assertTrue(config["EnforceWorkGroupConfiguration"])
        self.assertEqual(config["BytesScannedCutoffPerQuery"], 1073741824)
        self.assertEqual(
            config["ResultConfiguration"]["EncryptionConfiguration"][
                "EncryptionOption"
            ],
            "SSE_S3",
        )


if __name__ == "__main__":
    unittest.main()
