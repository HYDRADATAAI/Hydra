from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "validate_public_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_public_repository", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load public repository validator")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class WorkflowActionUsesTests(unittest.TestCase):
    def validate(self, workflow_text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow = root / ".github" / "workflows" / "example.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(workflow_text, encoding="utf-8")
            errors: list[str] = []
            with (
                patch.object(validator, "ROOT", root),
                patch.object(validator, "LEGACY_MUTABLE_WORKFLOW_USES", {}),
            ):
                validator.validate_workflow_action_uses(errors)
            return errors

    def test_pinned_external_action_and_local_action_are_allowed(self) -> None:
        errors = self.validate(
            "steps:\n"
            "  - uses: actions/checkout@"
            "0123456789abcdef0123456789abcdef01234567\n"
            "  - uses: ./local-action\n"
        )
        self.assertEqual(errors, [])

    def test_unlisted_mutable_reference_is_rejected(self) -> None:
        errors = self.validate("steps:\n  - uses: attacker/action@main\n")
        self.assertTrue(any("unlisted non-SHA" in error for error in errors))

    def test_decorated_and_aliased_block_keys_fail_closed(self) -> None:
        examples = (
            "- &step uses: attacker/action@main\n",
            "- !!str uses: attacker/action@main\n",
            '- &step !!str "uses": attacker/action@main\n',
            "- *uses_alias: attacker/action@main\n",
        )
        for example in examples:
            with self.subTest(example=example):
                errors = self.validate("steps:\n  " + example)
                self.assertTrue(
                    any("unsupported non-block workflow uses syntax" in error for error in errors),
                    errors,
                )

    def test_explicit_keys_fail_closed_including_continuations(self) -> None:
        examples = (
            "- ? uses\n  : attacker/action@main\n",
            "- ?\n    uses\n  : attacker/action@main\n",
            "- &mapping ? uses : attacker/action@main\n",
            "- ? !!str \"uses\"\n  : attacker/action@main\n",
        )
        for example in examples:
            with self.subTest(example=example):
                errors = self.validate("steps:\n  " + example)
                self.assertTrue(
                    any("unsupported non-block workflow uses syntax" in error for error in errors),
                    errors,
                )

    def test_flow_keys_and_multiline_flow_collections_fail_closed(self) -> None:
        examples = (
            "- {uses: attacker/action@main}\n",
            "- {&step uses: attacker/action@main}\n",
            '- {!!str "uses": attacker/action@main}\n',
            "- {*uses_alias: attacker/action@main}\n",
            "- {\n    uses: attacker/action@main\n  }\n",
        )
        for example in examples:
            with self.subTest(example=example):
                errors = self.validate("steps:\n  " + example)
                self.assertTrue(
                    any("unsupported non-block workflow uses syntax" in error for error in errors),
                    errors,
                )

    def test_multiline_quoted_keys_fail_closed(self) -> None:
        errors = self.validate(
            "steps:\n"
            '  - "u\\\n'
            "    ses\": attacker/action@main\n"
        )
        self.assertTrue(
            any("unsupported multiline quoted workflow syntax" in error for error in errors),
            errors,
        )

    def test_run_scalar_text_is_not_scanned_as_action_references(self) -> None:
        errors = self.validate(
            "steps:\n"
            "  - run: echo '{uses: attacker/action@main}'\n"
            "  - run: |\n"
            "      uses: attacker/action@main\n"
            "      - &anchor text\n"
            "      echo \"unfinished\n"
        )
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
