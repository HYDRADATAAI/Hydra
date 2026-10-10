import unittest

import yaml

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
