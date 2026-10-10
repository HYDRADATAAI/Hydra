import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import tools.validate_public_repository as validator
from tools.validate_public_repository import (
    workflow_action_ref_is_pinned,
    workflow_action_refs,
)


class WorkflowActionRefsTests(unittest.TestCase):
    def test_pin_policy_rejects_mutable_refs(self):
        digest = "0123456789abcdef0123456789abcdef01234567"
        self.assertTrue(workflow_action_ref_is_pinned(f"actions/checkout@{digest}"))
        self.assertFalse(workflow_action_ref_is_pinned("actions/checkout@v4"))
        self.assertFalse(workflow_action_ref_is_pinned("actions/checkout@main"))
        self.assertTrue(workflow_action_ref_is_pinned("./.github/actions/local"))
        self.assertTrue(
            workflow_action_ref_is_pinned("docker://alpine@sha256:" + "0" * 64)
        )
        self.assertFalse(workflow_action_ref_is_pinned("docker://alpine:3.20"))

    def test_rejects_duplicate_step_uses_in_both_orders(self):
        digest = "0123456789abcdef0123456789abcdef01234567"
        for refs in (
            (f"actions/checkout@{digest}", "actions/checkout@v4"),
            ("actions/checkout@v4", f"actions/checkout@{digest}"),
        ):
            workflow = (
                "jobs:\n"
                "  build:\n"
                "    steps:\n"
                "      - uses: " + "\n        uses: ".join(refs) + "\n"
            )
            with self.subTest(refs=refs):
                with self.assertRaisesRegex(yaml.YAMLError, "duplicate key"):
                    workflow_action_refs(workflow)

    def test_rejects_duplicate_reusable_workflow_uses_in_both_orders(self):
        digest = "0123456789abcdef0123456789abcdef01234567"
        for refs in (
            (f"example/repo/ci.yml@{digest}", "example/repo/ci.yml@main"),
            ("example/repo/ci.yml@main", f"example/repo/ci.yml@{digest}"),
        ):
            workflow = (
                "jobs:\n"
                "  reusable:\n"
                "    uses: " + "\n    uses: ".join(refs) + "\n"
            )
            with self.subTest(refs=refs):
                with self.assertRaisesRegex(yaml.YAMLError, "duplicate key"):
                    workflow_action_refs(workflow)

    def test_rejects_unhashable_collection_mapping_key(self):
        workflow = "jobs:\n  build:\n    ? [unhashable]\n    : value\n"

        with self.assertRaisesRegex(
            yaml.constructor.ConstructorError, "unhashable key"
        ):
            workflow_action_refs(workflow)

    def test_rejects_yaml_merge_keys(self):
        workflow = """defaults: &defaults
  runs-on: ubuntu-latest
jobs:
  build:
    <<: *defaults
    steps: []
"""

        with self.assertRaisesRegex(
            yaml.constructor.ConstructorError, "unsupported YAML merge key"
        ):
            workflow_action_refs(workflow)

    def test_invalid_yaml_key_errors_include_workflow_path(self):
        invalid_workflows = {
            "unhashable collection key": (
                "jobs:\n  build:\n    ? [unhashable]\n    : value\n",
                "unhashable key",
            ),
            "merge key": (
                "defaults: &defaults\n"
                "  runs-on: ubuntu-latest\n"
                "jobs:\n"
                "  build:\n"
                "    <<: *defaults\n"
                "    steps: []\n",
                "unsupported YAML merge key",
            ),
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow_directory = root / ".github" / "workflows"
            shutil.copytree(
                Path(validator.ROOT) / ".github" / "workflows",
                workflow_directory,
            )
            shutil.copy2(Path(validator.ROOT) / "README.md", root / "README.md")
            workflow_path = workflow_directory / "invalid.yml"

            for case, (workflow, message) in invalid_workflows.items():
                with self.subTest(case=case):
                    workflow_path.write_text(workflow, encoding="utf-8")
                    errors = []
                    with (
                        patch.object(validator, "ROOT", root),
                        patch.object(
                            validator, "validate_manifest_v2_replay_contract"
                        ),
                        patch.object(
                            validator, "validate_pre_upload_verifier_contract"
                        ),
                    ):
                        validator.validate_ci_contract(errors)

                    matching_errors = [
                        error
                        for error in errors
                        if "unable to parse workflow actions" in error
                    ]
                    self.assertEqual(len(matching_errors), 1, errors)
                    self.assertIn(".github/workflows/invalid.yml", matching_errors[0])
                    self.assertIn(message, matching_errors[0])
                    self.assertIn("line", matching_errors[0])

    def test_reads_yaml_uses_fields_and_resolves_aliases(self):
        workflow = """jobs:
  reusable:
    uses: example/repo/.github/workflows/ci.yml@0123456789abcdef0123456789abcdef01234567
  test:
    steps:
      - uses: &checkout actions/checkout@0123456789abcdef0123456789abcdef01234567
      - uses: *checkout
      - {"uses": "actions/setup-python@0123456789abcdef0123456789abcdef01234567"}
      - "uses": 'actions/upload-artifact@0123456789abcdef0123456789abcdef01234567'
      - run: |
          uses: example/not-an-action@v4
      - uses: ./.github/actions/local
"""
        self.assertEqual(
            workflow_action_refs(workflow),
            [
                "example/repo/.github/workflows/ci.yml@0123456789abcdef0123456789abcdef01234567",
                "actions/checkout@0123456789abcdef0123456789abcdef01234567",
                "actions/checkout@0123456789abcdef0123456789abcdef01234567",
                "actions/setup-python@0123456789abcdef0123456789abcdef01234567",
                "actions/upload-artifact@0123456789abcdef0123456789abcdef01234567",
                "./.github/actions/local",
            ],
        )


if __name__ == "__main__":
    unittest.main()
