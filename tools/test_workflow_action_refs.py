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

        self.assertIn(
            "$baselineHash = $report.baseline_source_sha256", step
        )
        self.assertIn(
            "$candidateHash = $report.candidate_source_sha256", step
        )
        self.assertIn("$baselineHash -isnot [string]", step)
        self.assertIn("$candidateHash -isnot [string]", step)
        baseline_format_check = (
            r"[regex]::IsMatch($baselineHash, '\A[0-9a-f]{64}\z')"
        )
        candidate_format_check = (
            r"[regex]::IsMatch($candidateHash, '\A[0-9a-f]{64}\z')"
        )
        comparison = "if ($baselineHash -cne $candidateHash)"
        precomparison_checks = (
            "$baselineHash -isnot [string]",
            "$candidateHash -isnot [string]",
            baseline_format_check,
            candidate_format_check,
        )
        for check in precomparison_checks:
            self.assertIn(check, step)
            self.assertLess(step.index(check), step.index(comparison))

        mismatch_outputs = step[
            step.index(comparison) : step.index(
                "foreach ($name in $required)", step.index(comparison)
            )
        ]
        for output in (
            "repaired_types.json",
            "repaired_types.log",
            "existing_admission.json",
            "existing_admission.log",
            "existing_bridge.json",
            "existing_bridge.log",
        ):
            self.assertIn(f"'{output}'", mismatch_outputs)

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
