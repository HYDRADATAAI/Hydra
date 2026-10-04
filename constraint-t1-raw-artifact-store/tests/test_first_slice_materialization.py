from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hydra_constraint_t1_raw.first_slice_materialization import (
    FirstSliceMaterializationError,
    materialize_capture_plan,
    validate_public_materialization_attestation,
)


class FirstSliceMaterializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "public-repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.captures = self.base / "captures"
        self.captures.mkdir()

        (self.captures / "a.html").write_bytes(b"<html>A</html>\n")
        (self.captures / "b.pdf").write_bytes(b"%PDF-synthetic-B\n")

        self.registry = {
            "slice_id": "SLICE-X",
            "sources": [
                {"source_id": "SRC-A", "url": "https://example.invalid/a"},
                {"source_id": "SRC-B", "url": "https://example.invalid/b"},
            ],
        }
        self.plan = {
            "schema_version": "hydra-constraint-first-slice-local-capture-plan/v1",
            "slice_id": "SLICE-X",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "release_id": "REL-SLICE-X-001",
            "release_created_at": "2026-09-26T13:10:00Z",
            "captures": [
                {
                    "source_id": "SRC-A",
                    "source_version_id": "SV-A-001",
                    "input_file": str(self.captures / "a.html"),
                    "content_type": "text/html",
                    "source_locator": "https://example.invalid/a",
                    "acquired_at": "2026-09-26T13:00:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
                {
                    "source_id": "SRC-B",
                    "source_version_id": "SV-B-001",
                    "input_file": str(self.captures / "b.pdf"),
                    "content_type": "application/pdf",
                    "source_locator": "https://example.invalid/b",
                    "acquired_at": "2026-09-26T13:01:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def run_plan(self, plan=None):
        return materialize_capture_plan(
            registry=self.registry,
            plan=self.plan if plan is None else plan,
            private_root=self.private,
            public_repo_root=self.repo,
        )

    def test_complete_source_set_materializes_but_unverified_admission_stays_blocked(self):
        attestation = self.run_plan()
        self.assertEqual(2, attestation["registry_source_count"])
        self.assertEqual(2, attestation["materialized_source_count"])
        self.assertEqual(0, attestation["ordinary_t2_eligible_count"])
        self.assertEqual(2, attestation["ordinary_t2_blocked_count"])
        self.assertTrue(attestation["all_registry_sources_materialized"])
        self.assertFalse(attestation["all_sources_ordinary_t2_eligible"])
        self.assertTrue(all(row["ordinary_t2_eligible"] is False for row in attestation["members"]))
        self.assertEqual(["SV-A-001", "SV-B-001"], [row["source_version_id"] for row in attestation["members"]])
        self.assertFalse(attestation["strict_historical_replay_promoted"])
        self.assertFalse(attestation["historical_availability_backdated"])
        self.assertTrue(all(
            row["available_at"] == row["acquired_at"]
            for row in attestation["members"]
        ))

    def test_capture_plan_must_cover_exact_registry_source_set(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"] = bad["captures"][:1]
        with self.assertRaisesRegex(FirstSliceMaterializationError, "exactly match registry"):
            self.run_plan(bad)

    def test_capture_plan_and_registry_reject_whitespace_slice_ids_before_store_creation(self):
        for slice_id in ("   ", "\t\n", "\u2003", "\u00a0"):
            with self.subTest(boundary="plan", slice_id=repr(slice_id)):
                bad = copy.deepcopy(self.plan)
                bad["slice_id"] = slice_id
                self.assertFalse(self.private.exists())
                with self.assertRaisesRegex(FirstSliceMaterializationError, "slice_id required"):
                    self.run_plan(bad)
                self.assertFalse(self.private.exists())

            with self.subTest(boundary="registry", slice_id=repr(slice_id)):
                bad_registry = copy.deepcopy(self.registry)
                bad_plan = copy.deepcopy(self.plan)
                bad_registry["slice_id"] = slice_id
                bad_plan["slice_id"] = slice_id
                self.assertFalse(self.private.exists())
                with self.assertRaisesRegex(FirstSliceMaterializationError, "registry.slice_id required"):
                    materialize_capture_plan(
                        registry=bad_registry,
                        plan=bad_plan,
                        private_root=self.private,
                        public_repo_root=self.repo,
                    )
                self.assertFalse(self.private.exists())

    def test_whitespace_content_type_is_rejected_before_private_store_creation(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][1]["content_type"] = "   "
        self.assertFalse(self.private.exists())
        with self.assertRaisesRegex(FirstSliceMaterializationError, "SRC-B: content_type required"):
            self.run_plan(bad)
        self.assertFalse(self.private.exists())

    def test_invalid_last_body_is_rejected_before_any_store_write(self):
        cases = (
            ("application/pdf", b"<html>Not a PDF</html>", "PDF signature"),
            ("application/pdf", b"<!doctype html><html><h1>403 Forbidden</h1></html>", "PDF signature"),
            ("text/html; charset=UTF-8", b"Not an HTML body", "HTML source body"),
            ("application/octet-stream", b"", "empty"),
        )
        for index, (content_type, raw, diagnostic) in enumerate(cases):
            with self.subTest(content_type=content_type):
                self.private = self.base / f"private-invalid-{index}"
                plan = copy.deepcopy(self.plan)
                plan["captures"][1]["content_type"] = content_type
                (self.captures / "b.pdf").write_bytes(raw)
                with self.assertRaisesRegex(FirstSliceMaterializationError, diagnostic):
                    self.run_plan(plan)
                self.assertFalse(self.private.exists())

    def test_error_interstitial_bodies_are_rejected_before_any_store_write(self):
        for marker in (b"ACCESS DENIED", b"CAPTCHA", b"403 FORBIDDEN", b"404 NOT FOUND"):
            for prefix, suffix in (
                (b"<!DOCTYPE html><html>", b"</html>"),
                (b"<!DOCTYPE html><html><head><title>", b"</title></head></html>"),
                (b"<!DOCTYPE html><html><body><h1>", b"</h1></body></html>"),
                (b"<!DOCTYPE html><html><body><h2>", b"</h2></body></html>"),
            ):
                with self.subTest(marker=marker, prefix=prefix):
                    self.private = self.base / f"private-error-{marker.decode().replace(' ', '-')}-{len(prefix)}"
                    plan = copy.deepcopy(self.plan)
                    plan["captures"][1]["content_type"] = "text/html; charset=UTF-8"
                    (self.captures / "b.pdf").write_bytes(prefix + marker + suffix)
                    with self.assertRaisesRegex(FirstSliceMaterializationError, "error/interstitial"):
                        self.run_plan(plan)
                    self.assertFalse(self.private.exists())

    def test_visible_error_heading_normalizes_entities_and_inline_markup(self):
        (self.captures / "a.html").write_bytes(
            b"<!doctype html><html><body><h1>Access&nbsp;<span>Denied</span></h1></body></html>"
        )
        with self.assertRaisesRegex(FirstSliceMaterializationError, "error/interstitial"):
            self.run_plan()
        self.assertFalse(self.private.exists())

    def test_late_body_read_failure_leaves_store_untouched(self):
        original_read = Path.read_bytes
        last_input = self.captures / "b.pdf"

        def read_or_fail(path):
            if path == last_input:
                raise OSError("synthetic read failure")
            return original_read(path)

        with patch.object(Path, "read_bytes", read_or_fail):
            with self.assertRaisesRegex(OSError, "synthetic read failure"):
                self.run_plan()
        self.assertFalse(self.private.exists())

    def test_pdf_body_markers_are_not_interstitial_evidence(self):
        for index, marker in enumerate((b"ACCESS DENIED", b"CAPTCHA", b"403 FORBIDDEN", b"404 NOT FOUND")):
            with self.subTest(marker=marker):
                self.private = self.base / f"private-pdf-report-{index}"
                self.plan["captures"][1]["content_type"] = "Application/PDF; version=1.7"
                (self.captures / "b.pdf").write_bytes(b"%PDF-1.7\n% Synthetic report topic: " + marker + b"\n")
                attestation = self.run_plan()
                self.assertEqual(2, attestation["materialized_source_count"])
                self.assertEqual(0, attestation["ordinary_t2_eligible_count"])

    def test_html_script_urls_and_hidden_text_are_not_interstitial_evidence(self):
        (self.captures / "a.html").write_bytes(
            b'<!doctype html><html><head><title>Quarterly results</title>'
            b'<script src="https://example.invalid/recaptcha/api.js"></script>'
            b'<style>/* access denied */</style></head><body>'
            b'<!-- 403 forbidden --><template>404 not found</template>'
            b'<h1>Quarterly results</h1><p>Orders increased.</p></body></html>'
        )
        self.assertEqual(2, self.run_plan()["materialized_source_count"])

    def test_html_article_mentions_are_not_interstitial_evidence(self):
        (self.captures / "a.html").write_bytes(
            b'<!doctype html><html><head><title>Service report</title></head>'
            b'<body><h1>Service report</h1><p>The release corrected 404 Not Found '
            b'and 403 Forbidden errors and improved CAPTCHA handling. Earlier '
            b'access denied incidents are documented here.</p></body></html>'
        )
        self.assertEqual(2, self.run_plan()["materialized_source_count"])

    def test_persistence_uses_preflight_bytes_if_staged_file_changes(self):
        original_read = Path.read_bytes
        first_input = self.captures / "a.html"
        original_bytes = original_read(first_input)

        def read_and_change_earlier_input(path):
            raw = original_read(path)
            if path == self.captures / "b.pdf":
                first_input.write_bytes(b"<html>changed after preflight</html>")
            return raw

        with patch.object(Path, "read_bytes", read_and_change_earlier_input):
            attestation = self.run_plan()
        self.assertEqual(
            hashlib.sha256(original_bytes).hexdigest(),
            attestation["members"][0]["artifact_sha256"],
        )

    def test_small_generic_bodies_remain_supported_without_admission(self):
        plan = copy.deepcopy(self.plan)
        plan["captures"][1]["content_type"] = "application/octet-stream"
        (self.captures / "b.pdf").write_bytes(b"synthetic generic body")
        attestation = self.run_plan(plan)
        self.assertEqual(2, attestation["materialized_source_count"])
        self.assertEqual(0, attestation["ordinary_t2_eligible_count"])
        self.assertFalse(attestation["strict_historical_replay_promoted"])

    def test_unregistered_source_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["source_id"] = "SRC-UNKNOWN"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "unregistered source"):
            self.run_plan(bad)

    def test_registry_locator_substitution_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["source_locator"] = "https://example.invalid/imposter"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "exactly match registry URL"):
            self.run_plan(bad)

    def test_raw_input_inside_public_repo_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        public_capture = self.repo / "raw-source.html"
        public_capture.write_bytes(b"should-not-be-public\n")
        bad["captures"][0]["input_file"] = str(public_capture)
        with self.assertRaisesRegex(FirstSliceMaterializationError, "must not live inside"):
            self.run_plan(bad)

    def test_caller_cannot_backdate_available_at_in_conservative_mode(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["available_at"] = "2023-01-01T00:00:00Z"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "must not be supplied"):
            self.run_plan(bad)

    def test_historical_availability_mode_is_not_silently_supported(self):
        bad = copy.deepcopy(self.plan)
        bad["availability_mode"] = "HISTORICAL_PROOF"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "only ACQUISITION_TIME_CONSERVATIVE"):
            self.run_plan(bad)

    def test_release_cannot_precede_latest_acquisition(self):
        bad = copy.deepcopy(self.plan)
        bad["release_created_at"] = "2026-09-26T13:00:30Z"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "cannot precede"):
            self.run_plan(bad)

    def test_quarantined_member_materializes_but_does_not_become_t2_eligible(self):
        plan = copy.deepcopy(self.plan)
        plan["captures"][1]["processing_disposition"] = "QUARANTINED"
        attestation = self.run_plan(plan)
        self.assertEqual(2, attestation["materialized_source_count"])
        self.assertEqual(0, attestation["ordinary_t2_eligible_count"])
        self.assertEqual(2, attestation["ordinary_t2_blocked_count"])
        self.assertFalse(attestation["all_sources_ordinary_t2_eligible"])
        self.assertEqual(["ELIGIBLE", "QUARANTINED"], [row["processing_disposition"] for row in attestation["members"]])


    def test_public_attestation_validates_without_private_raw_bytes(self):
        attestation = self.run_plan()
        validate_public_materialization_attestation(
            attestation=attestation,
            registry=self.registry,
        )

    def test_public_attestation_and_registry_reject_whitespace_slice_ids(self):
        attestation = self.run_plan()
        for slice_id in ("   ", "\t\n", "\u2003", "\u00a0"):
            with self.subTest(boundary="attestation", slice_id=repr(slice_id)):
                malformed = copy.deepcopy(attestation)
                malformed["slice_id"] = slice_id
                with self.assertRaisesRegex(FirstSliceMaterializationError, "attestation slice_id mismatch"):
                    validate_public_materialization_attestation(
                        attestation=malformed,
                        registry=self.registry,
                    )

            with self.subTest(boundary="registry", slice_id=repr(slice_id)):
                malformed_registry = copy.deepcopy(self.registry)
                malformed_registry["slice_id"] = slice_id
                malformed_attestation = copy.deepcopy(attestation)
                malformed_attestation["slice_id"] = slice_id
                with self.assertRaisesRegex(FirstSliceMaterializationError, "registry.slice_id required"):
                    validate_public_materialization_attestation(
                        attestation=malformed_attestation,
                        registry=malformed_registry,
                    )

    def test_attestation_validator_rejects_non_mapping_roots(self):
        attestation = self.run_plan()
        with self.assertRaisesRegex(
            FirstSliceMaterializationError,
            "attestation object required",
        ):
            validate_public_materialization_attestation(
                attestation=None,
                registry=self.registry,
            )
        with self.assertRaisesRegex(
            FirstSliceMaterializationError,
            "registry object required",
        ):
            validate_public_materialization_attestation(
                attestation=attestation,
                registry=None,
            )

    def test_member_eligibility_requires_a_boolean(self):
        attestation = self.run_plan()
        for member in attestation["members"]:
            self.assertIs(type(member["ordinary_t2_eligible"]), bool)
        for value in (0, 1, "false", None):
            with self.subTest(value=value):
                malformed = copy.deepcopy(attestation)
                malformed["members"][0]["ordinary_t2_eligible"] = value
                with self.assertRaisesRegex(
                    FirstSliceMaterializationError,
                    "ordinary_t2_eligible must be a boolean",
                ):
                    validate_public_materialization_attestation(
                        attestation=malformed,
                        registry=self.registry,
                    )

    def test_attestation_counts_require_exact_integers(self):
        attestation = self.run_plan()
        for field in (
            "registry_source_count",
            "materialized_source_count",
            "ordinary_t2_eligible_count",
            "ordinary_t2_blocked_count",
        ):
            with self.subTest(field=field):
                malformed = copy.deepcopy(attestation)
                invalid_values = [float(malformed[field])]
                if field == "ordinary_t2_eligible_count":
                    invalid_values.append(False)
                for value in invalid_values:
                    with self.subTest(value=value):
                        malformed = copy.deepcopy(attestation)
                        malformed[field] = value
                        with self.assertRaisesRegex(
                            FirstSliceMaterializationError,
                            f"{field} must be an exact integer",
                        ):
                            validate_public_materialization_attestation(
                                attestation=malformed,
                                registry=self.registry,
                            )

    def test_boolean_aggregate_requires_a_boolean(self):
        attestation = self.run_plan()
        for value in (0, 0.0):
            with self.subTest(value=value):
                malformed = copy.deepcopy(attestation)
                malformed["all_sources_ordinary_t2_eligible"] = value
                with self.assertRaisesRegex(
                    FirstSliceMaterializationError,
                    "all_sources_ordinary_t2_eligible drift",
                ):
                    validate_public_materialization_attestation(
                        attestation=malformed,
                        registry=self.registry,
                    )

    def test_member_metadata_requires_valid_types_and_values(self):
        attestation = self.run_plan()
        invalid_members = (
            ("byte_length", 0),
            ("byte_length", True),
            ("content_type", "   "),
            ("processing_disposition", "UNKNOWN"),
        )
        expected_errors = {
            "byte_length": "members\\[0\\]\\.byte_length invalid",
            "content_type": "members\\[0\\]\\.content_type invalid",
            "processing_disposition": "members\\[0\\]\\.processing_disposition invalid",
        }
        for field, value in invalid_members:
            with self.subTest(field=field, value=value):
                malformed = copy.deepcopy(attestation)
                malformed["members"][0][field] = value
                with self.assertRaisesRegex(
                    FirstSliceMaterializationError,
                    expected_errors[field],
                ):
                    validate_public_materialization_attestation(
                        attestation=malformed,
                        registry=self.registry,
                    )

    def test_public_attestation_rejects_missing_root_field(self):
        attestation = self.run_plan()
        required_root_fields = {
            "schema_version",
            "slice_id",
            "capture_mode",
            "availability_mode",
            "network_acquisition_performed_by_materializer",
            "public_raw_content_published",
            "release_id",
            "release_sha256",
            "release_created_at",
            "registry_source_count",
            "materialized_source_count",
            "ordinary_t2_eligible_count",
            "ordinary_t2_blocked_count",
            "all_registry_sources_materialized",
            "all_sources_ordinary_t2_eligible",
            "strict_historical_replay_promoted",
            "historical_availability_backdated",
            "members",
        }
        self.assertEqual(set(attestation), required_root_fields)
        earlier_diagnostics = {
            "schema_version": "unsupported attestation schema",
            "slice_id": "attestation slice_id mismatch",
            "capture_mode": "attestation capture mode invalid",
            "availability_mode": "attestation availability mode invalid",
            "network_acquisition_performed_by_materializer": (
                "attestation claims network acquisition authority"
            ),
            "public_raw_content_published": "attestation claims raw public content",
            "strict_historical_replay_promoted": (
                "attestation improperly promotes strict historical replay"
            ),
            "historical_availability_backdated": (
                "attestation backdates historical availability"
            ),
        }
        for field in sorted(required_root_fields):
            with self.subTest(field=field):
                incomplete = dict(attestation)
                del incomplete[field]
                with self.assertRaises(FirstSliceMaterializationError) as raised:
                    validate_public_materialization_attestation(
                        attestation=incomplete,
                        registry=self.registry,
                    )
                self.assertEqual(
                    str(raised.exception),
                    earlier_diagnostics.get(
                        field,
                        "attestation root field set invalid",
                    ),
                )

    def test_public_attestation_rejects_private_path_leakage(self):
        attestation = self.run_plan()
        attestation["members"][0]["input_file"] = str(self.captures / "a.html")
        with self.assertRaisesRegex(FirstSliceMaterializationError, "private/raw path"):
            validate_public_materialization_attestation(
                attestation=attestation,
                registry=self.registry,
            )

    def test_public_attestation_rejects_member_digest_tamper(self):
        attestation = self.run_plan()
        attestation["members"][0]["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release SHA"):
            validate_public_materialization_attestation(
                attestation=attestation,
                registry=self.registry,
            )

    def test_replay_of_identical_capture_plan_is_idempotent(self):
        left = self.run_plan()
        right = self.run_plan()
        self.assertEqual(left, right)

    def test_unverified_capture_metadata_is_not_discarded(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["verification_status"] = "TIMESTAMP_UNVERIFIED"
        with self.assertRaises(FirstSliceMaterializationError):
            self.run_plan(bad)
        self.assertFalse(self.private.exists())

    def test_attestation_rejects_unverified_and_authority_extensions(self):
        good = self.run_plan()
        for field, value in (
            ("verification_status", "TIMESTAMP_UNVERIFIED"),
            ("canonical_admission_promoted", True),
            ("production_activation", True),
            ("capture_inbox", "D:\\PRIVATE\\unpublished"),
        ):
            for at_member in (False, True):
                with self.subTest(field=field, at_member=at_member):
                    bad = copy.deepcopy(good)
                    target = bad["members"][0] if at_member else bad
                    target[field] = value
                    with self.assertRaises(FirstSliceMaterializationError):
                        validate_public_materialization_attestation(
                            attestation=bad, registry=self.registry,
                        )

    def test_attestation_requires_member_byte_length_and_content_type(self):
        good = self.run_plan()
        for field in ("byte_length", "content_type"):
            with self.subTest(missing_field=field):
                bad = copy.deepcopy(good)
                del bad["members"][0][field]
                with self.assertRaises(FirstSliceMaterializationError):
                    validate_public_materialization_attestation(
                        attestation=bad, registry=self.registry,
                    )


if __name__ == "__main__":
    unittest.main()
