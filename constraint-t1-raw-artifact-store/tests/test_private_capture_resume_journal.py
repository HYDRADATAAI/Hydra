from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "private" / "Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1"


class PrivateCaptureResumeJournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_resume_journal_is_private_and_non_authoritative(self):
        self.assertIn("[string]$ResumeJournalPath", self.text)
        self.assertIn("hydra-constraint-private-capture-journal/v1", self.text)
        self.assertIn("authoritative = $false", self.text)
        self.assertIn('Assert-OutsideRepo -CandidatePath $ResumeJournalPath', self.text)

    def test_new_run_writes_journal_before_any_source_authority(self):
        self.assertIn("HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_CAPTURE_JOURNAL_", self.text)
        self.assertIn("Write-CaptureJournal -Journal $Journal -JournalPath $JournalPath", self.text)
        self.assertIn("capture_plan_written = $false", self.text)
        self.assertIn("t1_materialization_started = $false", self.text)
        self.assertIn("t1_release_written = $false", self.text)

    def test_each_successful_capture_is_journaled_with_hash_and_acquisition_time(self):
        self.assertIn("artifact_sha256 = $Hash", self.text)
        self.assertIn("byte_length = [int64]$Item.Length", self.text)
        self.assertIn("acquired_at = $AcquiredAt", self.text)
        self.assertIn("source_version_id = $SourceVersionId", self.text)
        self.assertIn("capture_method = $CaptureMethod", self.text)

    def test_resume_revalidates_bytes_before_reuse(self):
        self.assertIn("function Test-JournalEntry", self.text)
        self.assertIn("Resume journal source locator mismatch", self.text)
        self.assertIn("Resume journal content type mismatch", self.text)
        self.assertIn("Resume journal byte length mismatch", self.text)
        self.assertIn("Resume journal SHA-256 mismatch", self.text)
        self.assertIn("Resume journal entry is not ELIGIBLE", self.text)

    def test_resume_preserves_original_source_version_and_acquired_at(self):
        self.assertIn('source_version_id = [string]$ExistingEntry.source_version_id', self.text)
        self.assertIn('acquired_at = [string]$ExistingEntry.acquired_at', self.text)
        self.assertIn("CAPTURE_RESUME_OK", self.text)

    def test_completed_release_journal_cannot_be_resumed(self):
        self.assertIn('$LoadedJournal.t1_release_written -eq $true', self.text)
        self.assertIn("Resume journal already records a completed T1 release", self.text)

    def test_t1_authority_is_still_created_only_after_all_nine_captures(self):
        all_nine = self.text.index('if ($Captures.Count -ne 9)')
        plan = self.text.index('$CapturePlan = [ordered]@{')
        materializer = self.text.index("hydra_constraint_t1_raw.first_slice_cli")
        self.assertLess(all_nine, plan)
        self.assertLess(plan, materializer)

    def test_journal_state_tracks_plan_materialization_and_release(self):
        self.assertIn("$Journal.capture_plan_written = $true", self.text)
        self.assertIn("$Journal.t1_materialization_started = $true", self.text)
        self.assertIn("$Journal.t1_release_written = $true", self.text)


if __name__ == "__main__":
    unittest.main()
