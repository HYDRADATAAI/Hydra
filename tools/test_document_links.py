import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import validate_public_repository as validator


class DocumentLinkValidationTests(unittest.TestCase):
    def validate_markdown(self, root: Path, text: str) -> list[str]:
        docs = root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "README.md").write_text(text, encoding="utf-8")
        errors: list[str] = []
        with patch.object(validator, "ROOT", root):
            validator.validate_markdown_links(errors)
        return errors

    def test_reference_style_markdown_missing_target_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            errors = self.validate_markdown(
                root,
                "[guide][guide]\n\n[guide]: <missing/guide.md> \"Guide\"\n",
            )
        self.assertEqual(len(errors), 1)
        self.assertIn("missing/guide.md", errors[0])

    def test_inline_markdown_missing_target_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            errors = self.validate_markdown(
                Path(temporary), "[missing](missing.md)\n"
            )
        self.assertEqual(len(errors), 1)
        self.assertIn("missing.md", errors[0])

    def test_html_href_and_src_missing_targets_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            errors = self.validate_markdown(
                root,
                '<a href="missing/page.html">page</a>\n'
                '<img src="images/missing.png">\n',
            )
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("missing/page.html" in error for error in errors))
        self.assertTrue(any("images/missing.png" in error for error in errors))

    def test_balanced_and_escaped_parentheses_in_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs = root / "docs"
            docs.mkdir()
            (docs / "guide_(v2).md").write_text("guide", encoding="utf-8")
            markdown = (
                "[balanced](guide_(v2).md) "
                "[escaped](guide_\\(v2\\).md)\n"
            )
            self.assertEqual(
                validator.document_link_references(markdown),
                ["guide_(v2).md", "guide_(v2).md"],
            )
            errors = self.validate_markdown(root, markdown)
        self.assertEqual(errors, [])

    def test_code_spans_and_fences_are_not_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            markdown = (
                "Example `[missing](missing.md) <a href='also-missing.html'>`\n"
                "```html\n"
                "<a href='fenced-missing.html'>example</a>\n"
                "[example](fenced-missing.md)\n"
                "```\n"
            )
            self.assertEqual(validator.document_link_references(markdown), [])
            errors = self.validate_markdown(root, markdown)
        self.assertEqual(errors, [])

    def test_longer_tilde_fence_closer_hides_code_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            markdown = (
                "~~~html\n"
                "<a href='missing.html'>example</a>\n"
                "[example](missing.md)\n"
                "~~~~\n"
            )
            self.assertEqual(validator.document_link_references(markdown), [])
            errors = self.validate_markdown(root, markdown)
        self.assertEqual(errors, [])

    def test_outside_target_fails_when_old_sentinel_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".invalid-outside-repository-link").write_text(
                "sentinel", encoding="utf-8"
            )
            errors = self.validate_markdown(
                root, "[escape](../../outside.txt)\n"
            )
        self.assertEqual(len(errors), 1)
        self.assertIn("escapes repository", errors[0])

    def test_prose_with_closing_bracket_and_paren_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            errors = self.validate_markdown(
                Path(temporary), "The sequence ](missing.md) appears in prose.\n"
            )
        self.assertEqual(errors, [])

    def test_local_valid_and_external_references_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docs = root / "docs"
            docs.mkdir()
            (docs / "guide.md").write_text("guide", encoding="utf-8")
            markdown = (
                "[inline](guide.md#start) [reference][guide]\n"
                "[guide]: <guide.md?view=1> \"Guide\"\n"
                '<a href="https://example.com/page">external</a>\n'
                '<a href="mailto:team@example.com">email</a>\n'
                '<a href="#section">fragment</a>\n'
                '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">\n'
            )
            self.assertEqual(
                validator.document_link_references(markdown),
                [
                    "guide.md#start",
                    "guide.md?view=1",
                    "https://example.com/page",
                    "mailto:team@example.com",
                    "#section",
                    "data:image/gif;base64,R0lGODlhAQABAAAAACw=",
                ],
            )
            errors = self.validate_markdown(root, markdown)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
