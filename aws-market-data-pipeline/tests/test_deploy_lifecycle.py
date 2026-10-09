from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock

from deploy_lifecycle import LifecycleError, deploy, effective_stack_name, guard, teardown


def result(*, returncode=0, stdout="", stderr=""):
    return CompletedProcess(["stub"], returncode, stdout, stderr)


class DeployLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = {
            "STACK_NAME": "hydra-public-market-pipeline-demo-20261009",
            "AWS_REGION": "us-east-1",
            "GITHUB_REPOSITORY": "HYDRADATAAI/Hydra",
            "GITHUB_RUN_ID": "1234567890",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_ENV": str(Path(self.temp.name) / "github-env"),
        }
        self.tags = [
            {"Key": "hydra:github-repository", "Value": self.env["GITHUB_REPOSITORY"]},
            {"Key": "hydra:github-run-id", "Value": self.env["GITHUB_RUN_ID"]},
            {"Key": "hydra:github-run-attempt", "Value": self.env["GITHUB_RUN_ATTEMPT"]},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def test_stack_name_is_unique_per_run_attempt(self):
        self.assertEqual(
            effective_stack_name(self.env),
            "hydra-public-market-pipeline-demo-20261009-1234567890-2",
        )

    def test_guard_refuses_existing_stack_before_exporting_name(self):
        runner = Mock(return_value=result(stdout=json.dumps(
            {"Stacks": [{"StackName": "existing"}]}
        )))
        with self.assertRaisesRegex(LifecycleError, "refusing to update"):
            guard(env=self.env, runner=runner)
        self.assertEqual(runner.call_count, 1)
        self.assertFalse(Path(self.env["GITHUB_ENV"]).exists())

    def test_guard_accepts_only_explicit_missing_stack_response(self):
        runner = Mock(return_value=result(
            returncode=255, stderr="ValidationError: Stack with id x does not exist"
        ))
        name = guard(env=self.env, runner=runner)
        self.assertEqual(name, effective_stack_name(self.env))
        self.assertIn(f"STACK_NAME={name}\n", Path(self.env["GITHUB_ENV"]).read_text())

    def test_guard_fails_closed_on_other_aws_errors(self):
        runner = Mock(return_value=result(returncode=254, stderr="AccessDenied"))
        with self.assertRaisesRegex(LifecycleError, "unable to establish stack state"):
            guard(env=self.env, runner=runner)
        self.assertEqual(runner.call_count, 1)

    def test_failed_sam_deploy_does_not_export_bucket_names(self):
        runner = Mock(side_effect=[
            result(returncode=255, stderr="stack does not exist"),
            result(stdout="123456789012\n"),
            result(returncode=1, stderr="deployment failed"),
        ])
        with self.assertRaisesRegex(LifecycleError, "sam failed"):
            deploy(env=self.env, runner=runner)
        self.assertFalse(Path(self.env["GITHUB_ENV"]).exists())
        deploy_args = runner.call_args_list[-1].args[0]
        self.assertIn("hydra:github-run-id=1234567890", deploy_args)
        self.assertIn("hydra:github-run-attempt=2", deploy_args)

    def test_teardown_skips_unowned_stack_without_destructive_calls(self):
        runner = Mock(return_value=result(stdout=json.dumps(
            {"Stacks": [{"StackName": "other", "Tags": []}]}
        )))
        self.assertFalse(teardown(env=self.env, runner=runner))
        self.assertEqual(runner.call_count, 1)

    def test_teardown_skips_absent_stack(self):
        runner = Mock(return_value=result(
            returncode=255, stderr="stack does not exist"
        ))
        self.assertFalse(teardown(env=self.env, runner=runner))
        self.assertEqual(runner.call_count, 1)

    def test_teardown_empties_only_tagged_stack_buckets(self):
        stack = {"StackName": self.env["STACK_NAME"], "Tags": self.tags}
        resources = {"StackResourceSummaries": [
            {"LogicalResourceId": "RawBucket", "ResourceType": "AWS::S3::Bucket",
             "ResourceStatus": "CREATE_COMPLETE", "PhysicalResourceId": "owned-raw"},
            {"LogicalResourceId": "CuratedBucket", "ResourceType": "AWS::S3::Bucket",
             "ResourceStatus": "CREATE_COMPLETE", "PhysicalResourceId": "owned-curated"},
            {"LogicalResourceId": "OtherBucket", "ResourceType": "AWS::S3::Bucket",
             "ResourceStatus": "CREATE_COMPLETE", "PhysicalResourceId": "unrelated"},
        ]}
        responses = [
            result(stdout=json.dumps({"Stacks": [stack]})),
            result(stdout=json.dumps(resources)),
            result(stdout=json.dumps({"TagSet": self.tags})),
            result(stdout=json.dumps({"Versions": [{"Key": "a", "VersionId": "1"}]})),
            result(),
            result(stdout=json.dumps({"TagSet": []})),
            result(),
        ]
        runner = Mock(side_effect=responses)

        self.assertTrue(teardown(env=self.env, runner=runner))
        commands = [call.args[0] for call in runner.call_args_list]
        self.assertTrue(any("delete-objects" in command and "owned-raw" in command for command in commands))
        self.assertFalse(any("owned-curated" in command and "delete-objects" in command for command in commands))
        self.assertFalse(any("unrelated" in command for command in commands))
        self.assertEqual(commands[-1][:3], ["sam", "delete", "--stack-name"])


if __name__ == "__main__":
    unittest.main()
