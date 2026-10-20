from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from hydra_market_pipeline.cli import main


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/synthetic_market_events.csv"
ALIASES = ROOT / "config/symbol_aliases.json"


class CliOutputPathSafetyTests(unittest.TestCase):
    def _run_cli(self, output_dir: Path) -> tuple[int, str]:
        errors = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(errors):
            result = main(
                [
                    "--input",
                    str(INPUT),
                    "--aliases",
                    str(ALIASES),
                    "--output-dir",
                    str(output_dir),
                ]
            )
        return result, errors.getvalue()

    def _create_directory_symlink(self, link: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink creation unavailable: {exc}")

    def test_cli_rejects_symlinked_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            output_dir = root / "output"
            self._create_directory_symlink(output_dir, external)

            status, stderr = self._run_cli(output_dir)

            self.assertEqual(status, 2)
            self.assertIn("output directory path must not contain symlinks", stderr)
            self.assertEqual(list(external.iterdir()), [])

    def test_cli_rejects_symlinked_output_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            linked_parent = root / "linked-parent"
            self._create_directory_symlink(linked_parent, external)

            status, stderr = self._run_cli(linked_parent / "output")

            self.assertEqual(status, 2)
            self.assertIn("output directory path must not contain symlinks", stderr)
            self.assertEqual(list(external.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
