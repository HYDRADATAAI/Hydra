import unittest

from public_root_hygiene import tracked_path_violation


class TrackedPathHygieneTests(unittest.TestCase):
    def test_generated_outputs_under_public_samples_are_rejected(self) -> None:
        paths = (
            "governed-intelligence-sample/build/grounding/output_manifest.json",
            "market-data-pipeline-sample/build/demo/manifest.json",
            "sql-data-quality-sample/results/query.csv",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(
                    tracked_path_violation(path), "generated output directory"
                )

    def test_transfer_artifacts_are_rejected_outside_archive(self) -> None:
        paths = (
            "hydra-proof.zip",
            "tools/download/proof.zip.sha256",
            "docs/EXTRACT_hydra_proof.PS1",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(tracked_path_violation(path))

    def test_archive_is_an_explicit_transfer_artifact_exception(self) -> None:
        self.assertIsNone(tracked_path_violation("archive/hydra-proof.zip"))
        self.assertIsNone(
            tracked_path_violation("archive/governed/build/output_manifest.json")
        )

    def test_source_docs_and_committed_fixture_paths_are_allowed(self) -> None:
        paths = (
            "tools/build.py",
            "governed-intelligence-sample/src/bin/cli.py",
            "docs/results/expected.json",
            "market-data-pipeline-sample/data/raw/synthetic_market_events.csv",
            "docs/report (2).md",
            "constraint-runtime/build/generated.json",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(tracked_path_violation(path))

    def test_only_root_duplicate_download_names_are_rejected(self) -> None:
        self.assertEqual(
            tracked_path_violation("hydra-proof (2).zip"),
            "transfer bundle",
        )
        self.assertEqual(
            tracked_path_violation("copy (2).md"),
            "root-level duplicate download",
        )
        self.assertIsNone(tracked_path_violation("docs/report (2).md"))


if __name__ == "__main__":
    unittest.main()
