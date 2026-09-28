from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "private" / "Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1"


class Batch017PrivateCaptureExecutionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_operator_must_explicitly_authorize_public_acquisition(self):
        self.assertIn("[switch]$AuthorizedPublicAcquisition", self.text)
        self.assertIn("Explicit -AuthorizedPublicAcquisition is required", self.text)

    def test_existing_private_roots_are_defaults(self):
        self.assertIn('D:\\HYDRA_PRIVATE\\constraint\\raw', self.text)
        self.assertIn('D:\\HYDRA_PRIVATE\\constraint\\capture-staging', self.text)
        self.assertIn('D:\\HYDRA_PRIVATE\\constraint\\metadata', self.text)

    def test_script_reads_authoritative_registry_instead_of_hardcoding_source_urls(self):
        self.assertIn(
            "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json",
            self.text,
        )
        self.assertIn("$Registry.sources", self.text)
        self.assertIn("$Source.url", self.text)
        self.assertNotIn("eta-publications.lbl.gov/publications/united-states-data-center-energy-2025", self.text)

    def test_script_requires_exact_nine_source_registry(self):
        self.assertIn("@($Registry.sources).Count -ne 9", self.text)
        self.assertIn("$Captures.Count -ne 9", self.text)
        self.assertIn("Registered source IDs are not unique", self.text)

    def test_script_keeps_raw_and_metadata_outside_public_repo(self):
        self.assertIn("Assert-OutsideRepo", self.text)
        self.assertIn('-CandidatePath $PrivateRawRoot', self.text)
        self.assertIn('-CandidatePath $PrivateStagingRoot', self.text)
        self.assertIn('-CandidatePath $PrivateMetadataRoot', self.text)

    def test_script_does_not_supply_historical_available_at(self):
        self.assertIn('availability_mode = "ACQUISITION_TIME_CONSERVATIVE"', self.text)
        self.assertNotIn("available_at =", self.text)
        self.assertIn("HISTORICAL_BACKDATING=NO", self.text)

    def test_script_invokes_network_blind_t1_materializer_and_public_attestation_validator(self):
        self.assertIn("hydra_constraint_t1_raw.first_slice_cli", self.text)
        self.assertIn("validate_constraint_t1_first_slice_attestation.py", self.text)
        self.assertIn("--private-root $PrivateRawRoot", self.text)
        self.assertIn("--attestation-output $AttestationPath", self.text)

    def test_script_supports_reviewed_sanitized_har_for_exact_three_403_sources(self):
        self.assertIn("[string]$LbnlQueuedUpSanitizedHarPath", self.text)
        self.assertIn("[string]$FercOrder2023SanitizedHarPath", self.text)
        self.assertIn("[string]$Pjm2025YearInReviewSanitizedHarPath", self.text)
        self.assertIn('"SRC-LBNL-QUEUED-UP-2025" = @{', self.text)
        self.assertIn('"SRC-FERC-ORDER-2023-FACT-SHEET" = @{', self.text)
        self.assertIn('"SRC-PJM-2025-YEAR-IN-REVIEW-2026-01-08" = @{', self.text)
        self.assertIn('ExpectedText = "Queued Up: 2025 Edition"', self.text)
        self.assertIn(
            'ExpectedText = "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements"',
            self.text,
        )
        self.assertIn(
            'ExpectedText = "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand"',
            self.text,
        )
        self.assertIn("hydra_constraint_t1_raw.browser_response_capture", self.text)
        self.assertIn("--exact-url $Uri", self.text)
        self.assertIn("--expected-text $ExpectedText", self.text)

    def test_script_har_fallback_is_allowlisted_not_generic_for_all_sources(self):
        self.assertIn("$Fallback = $BrowserHarFallbacks[$SourceId]", self.text)
        self.assertIn("if ($null -ne $Fallback -and $Fallback.HarPath)", self.text)
        self.assertIn("if ($null -ne $Fallback)", self.text)
        self.assertNotIn("SanitizedHarPathBySourceId", self.text)

    def test_script_does_not_replay_browser_cookies_or_copy_curl(self):
        self.assertNotIn("cf_clearance", self.text)
        self.assertNotIn("Copy as cURL", self.text)
        self.assertNotIn("-Headers @{", self.text)
        self.assertNotIn("Cookie", self.text)

    def test_script_never_claims_replay_or_canonical_promotion(self):
        self.assertIn("ORDINARY_REPLAY_PROMOTED=NO", self.text)
        self.assertIn("CANONICAL_ADMISSION_PROMOTED=NO", self.text)
        self.assertIn("RAW_BODIES_PUBLISHED_TO_GIT=NO", self.text)
        self.assertIn("CLOUDFLARE_BYPASS_ATTEMPTED=NO", self.text)
        self.assertIn("LINKED_REPORT_SUBSTITUTED=NO", self.text)
        self.assertIn("RENDERED_DOM_USED=NO", self.text)


if __name__ == "__main__":
    unittest.main()
