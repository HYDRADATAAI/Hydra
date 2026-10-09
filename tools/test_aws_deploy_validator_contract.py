from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from tools.validate_public_repository import athena_success_commands_are_valid


class AthenaDeployValidatorContractTests(unittest.TestCase):
    def test_actual_athena_workflow_step_is_valid(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.load(
            (root / ".github/workflows/aws-market-data-deploy.yml").read_text(
                encoding="utf-8"
            ),
            Loader=yaml.BaseLoader,
        )
        steps = workflow["jobs"]["deploy-and-verify"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Run bounded Athena verification query"
        )
        self.assertTrue(athena_success_commands_are_valid(step.get("run")))

    def test_missing_run_filter_does_not_satisfy_contract(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.load(
            (root / ".github/workflows/aws-market-data-deploy.yml").read_text(
                encoding="utf-8"
            ),
            Loader=yaml.BaseLoader,
        )
        steps = workflow["jobs"]["deploy-and-verify"]["steps"]
        step = next(
            step
            for step in steps
            if step.get("name") == "Run bounded Athena verification query"
        )
        invalid = step["run"].replace(" WHERE pipeline_run_id = '$RUN_ID'", "")
        self.assertFalse(athena_success_commands_are_valid(invalid))

    def test_comment_only_commands_do_not_satisfy_contract(self):
        script = """if [[ "$state" == "SUCCEEDED" ]]; then
  # aws athena get-query-results --query-execution-id "$QUERY_ID" > "$SAMPLE_DIR/build/deployed/athena_query_results.json"
  # python "$SAMPLE_DIR/verify_athena_query_results.py" --results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" --github-env "$GITHUB_ENV"
fi
if [[ "$state" == "FAILED" || "$state" == "CANCELLED" ]]; then
  exit 1
fi
"""
        self.assertFalse(athena_success_commands_are_valid(script))

    def test_space_after_continuation_backslash_is_not_accepted(self):
        script = """if [[ "$state" == "SUCCEEDED" ]]; then
  aws athena get-query-results --query-execution-id "$QUERY_ID" > "$SAMPLE_DIR/build/deployed/athena_query_results.json"
  python "$SAMPLE_DIR/verify_athena_query_results.py" \\
    --results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" \\
    --github-env "$GITHUB_ENV"
fi
if [[ "$state" == "FAILED" || "$state" == "CANCELLED" ]]; then
  exit 1
fi
"""
        invalid = script.replace(chr(92) + "\n", chr(92) + " \n")
        self.assertFalse(athena_success_commands_are_valid(invalid))


if __name__ == "__main__":
    unittest.main()
