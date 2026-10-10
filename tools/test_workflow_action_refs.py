import unittest
from pathlib import Path

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

    def test_receipt_workflow_validates_hashes_before_comparison(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (
            root / ".github/workflows/nyx-thread-g-receipt-windows.yml"
        ).read_text(encoding="utf-8")
        step = workflow.split(
            "- name: Verify expected receipt outputs", 1
        )[1].split("- name: Preserve exact results", 1)[0]

        required_outputs = (
            "$required = @('baseline.json', 'baseline.log', "
            "'RESULT.json', 'SOURCE_HASHES.json')"
        )
        validate_hashes = (
            "$conditionalRequiredJson = python -B "
            "tools/thread_g_receipt_validation.py $reportPath"
        )
        fail_closed = (
            "if ($LASTEXITCODE -ne 0) { "
            "throw 'RESULT.json hash validation failed' }"
        )
        append_outputs = (
            "$required += @(ConvertFrom-Json -InputObject "
            "$conditionalRequiredJson)"
        )
        ordered_checks = (
            required_outputs,
            "$reportPath = Join-Path $root 'RESULT.json'",
            "if (Test-Path -LiteralPath $reportPath -PathType Leaf) {",
            validate_hashes,
            fail_closed,
            append_outputs,
            "foreach ($name in $required) {",
            "$path = Join-Path $root $name",
            'if (-not (Test-Path -LiteralPath $path -PathType Leaf)) '
            '{ throw "Expected receipt output missing: $name" }',
        )
        previous_index = -1
        for check in ordered_checks:
            self.assertIn(check, step)
            self.assertGreater(step.index(check), previous_index)
            previous_index = step.index(check)
        self.assertIn(
            validate_hashes + "\n            " + fail_closed
            + "\n            " + append_outputs,
            step,
        )

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
