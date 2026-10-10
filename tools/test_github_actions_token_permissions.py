import tempfile
import unittest
from pathlib import Path

import yaml

from tools.validate_github_actions_token_permissions import (
    DEPLOY_PERMISSIONS,
    validate_repository,
    validate_workflow,
)


class GitHubActionsTokenPermissionsTests(unittest.TestCase):
    def validate_yaml(self, relative_path, text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return validate_workflow(path, yaml.safe_load(text), root)

    def test_accepts_baseline_permissions(self):
        errors = self.validate_yaml(
            ".github/workflows/example.yml",
            "permissions:\n  contents: read\njobs:\n  check:\n    runs-on: ubuntu-latest\n",
        )
        self.assertEqual(errors, [])

    def test_rejects_broader_permission_values_and_scopes(self):
        cases = (
            "permissions:\n  contents: write\njobs: {}\n",
            "permissions:\n  contents: read\n  actions: write\njobs: {}\n",
            "permissions: write-all\njobs: {}\n",
        )
        for workflow in cases:
            with self.subTest(workflow=workflow):
                errors = self.validate_yaml(".github/workflows/example.yml", workflow)
                self.assertTrue(any("top-level permissions" in error for error in errors))

    def test_requires_exact_deploy_exception(self):
        workflow = (
            "permissions:\n  contents: read\n  id-token: write\n"
            "jobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
        )
        path = Path(".github/workflows/aws-market-data-deploy.yml")
        self.assertEqual(validate_workflow(path, yaml.safe_load(workflow), Path(".")), [])
        self.assertEqual(
            DEPLOY_PERMISSIONS, {"contents": "read", "id-token": "write"}
        )

    def test_rejects_deploy_exception_in_other_workflows(self):
        errors = self.validate_yaml(
            ".github/workflows/example.yml",
            "permissions:\n  contents: read\n  id-token: write\njobs: {}\n",
        )
        self.assertTrue(any("top-level permissions" in error for error in errors))

    def test_rejects_job_level_permission_overrides(self):
        errors = self.validate_yaml(
            ".github/workflows/example.yml",
            "permissions:\n  contents: read\njobs:\n  check:\n"
            "    permissions:\n      contents: write\n",
        )
        self.assertTrue(any("job 'check'" in error for error in errors))

    def test_rejects_missing_top_level_permissions(self):
        errors = self.validate_yaml(
            ".github/workflows/example.yml",
            "jobs:\n  check:\n    runs-on: ubuntu-latest\n",
        )
        self.assertTrue(any("top-level permissions" in error for error in errors))

    def test_repository_scan_checks_each_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "good.yml").write_text(
                "permissions:\n  contents: read\njobs: {}\n", encoding="utf-8"
            )
            (workflows / "bad.yml").write_text(
                "permissions:\n  contents: write\njobs: {}\n", encoding="utf-8"
            )
            errors = validate_repository(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("bad.yml", errors[0])


if __name__ == "__main__":
    unittest.main()
