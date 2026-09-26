from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "tools"
    / "private"
    / "Start-HYDRAConstraintFirstSliceCaptureFromAnywhere_V001_20260926.ps1"
)


class WindowsWorkstationBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_defaults_to_actual_hydra_repo_path(self):
        self.assertIn('D:\\HYDRA_GITHUB\\Hydra', self.text)
        self.assertNotIn('D:\\HYDRA\\_GITHUB\\Hydra', self.text)

    def test_validates_repository_and_remote_before_git_mutation(self):
        self.assertIn('Join-Path $RepoRoot ".git"', self.text)
        self.assertIn("rev-parse --show-toplevel", self.text)
        self.assertIn("remote get-url $RemoteName", self.text)
        self.assertIn("HYDRADATAAI/Hydra", self.text)
        self.assertIn("Unexpected '$RemoteName' remote", self.text)

    def test_refuses_tracked_local_changes(self):
        self.assertIn("status --porcelain=v1 --untracked-files=no", self.text)
        self.assertIn("tracked working tree is not clean", self.text)

    def test_fetches_and_fast_forwards_only_canonical_capture_branch(self):
        self.assertIn(
            "constraint/t1-private-capture-execution-packet-20260926",
            self.text,
        )
        self.assertIn('Invoke-Git -Arguments @("checkout", $CaptureBranch)', self.text)
        self.assertIn(
            'Invoke-Git -Arguments @("merge", "--ff-only", "$RemoteName/$CaptureBranch")',
            self.text,
        )
        self.assertNotIn("git reset --hard", self.text)
        self.assertNotIn("stash", self.text)

    def test_invokes_canonical_capture_with_explicit_authorization(self):
        self.assertIn(
            "Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1",
            self.text,
        )
        self.assertIn('"-AuthorizedPublicAcquisition"', self.text)
        self.assertIn('"HYDRA_WORKSTATION_BOOTSTRAP=PASS"', self.text)
        self.assertIn('"HYDRA_WORKSTATION_CAPTURE=PASS"', self.text)

    def test_does_not_create_t1_authority_itself(self):
        self.assertNotIn("first_slice_cli", self.text)
        self.assertNotIn("RawArtifactStore", self.text)
        self.assertNotIn("release_id", self.text)
        self.assertNotIn("capture_plan", self.text)


if __name__ == "__main__":
    unittest.main()
