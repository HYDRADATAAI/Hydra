"""Windows-only coexistence probes for PR119 containment plus PR143 consistency.

Execute on the exact candidate: python -B temporal_coexistence_probe.py --repo D:\\candidate
Uses synthetic in-memory metadata only. No network, private capture or source writes.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import unittest


def rebind(record):
    release = build_release_manifest(
        release_id=record["release_id"], created_at=record["release_created_at"],
        receipts=record["members"],
    )
    record["release_sha256"] = release["release_sha256"]


def rehash(packet):
    payload = {k: v for k, v in packet.items() if k != "packet_sha256"}
    packet["packet_sha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TemporalCoexistenceTests(unittest.TestCase):
    def first_slice(self, second_time="2026-09-26T09:00:00-04:00"):
        members = []
        for name, time, a, r in (
            ("A", "2026-09-26T13:00:00Z", "a", "b"),
            ("B", second_time, "c", "d"),
            ("C", "2026-09-26T13:01:00Z", "e", "f"),
        ):
            members.append({
                "source_id": "SRC-" + name, "source_version_id": "SV-" + name,
                "artifact_sha256": a * 64, "receipt_sha256": r * 64,
                "byte_length": 1, "content_type": "text/plain",
                "acquired_at": time, "available_at": time,
                "processing_disposition": "ELIGIBLE", "ordinary_t2_eligible": False,
            })
        registry = {"slice_id": "SYNTHETIC-COEXISTENCE", "sources": [
            {"source_id": m["source_id"],
             "url": "https://example.invalid/" + m["source_id"]}
            for m in members
        ]}
        record = {
            "schema_version": ATTESTATION_SCHEMA, "slice_id": registry["slice_id"],
            "capture_mode": "OFFLINE_REVIEWED_LOCAL_BYTES",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "network_acquisition_performed_by_materializer": False,
            "public_raw_content_published": False,
            "release_id": "REL-SYNTHETIC-COEXISTENCE",
            "release_created_at": "2026-09-26T13:10:00Z",
            "registry_source_count": len(members), "materialized_source_count": len(members),
            "ordinary_t2_eligible_count": 0, "ordinary_t2_blocked_count": len(members),
            "all_registry_sources_materialized": True,
            "all_sources_ordinary_t2_eligible": False,
            "strict_historical_replay_promoted": False,
            "historical_availability_backdated": False, "members": members,
        }
        rebind(record)
        return registry, record

    def packet(self, registry, record):
        return build_replay_lineage_packet(attestation=record, registry=registry)

    def assert_contained(self, packet, registry):
        self.assertIs(packet["ordinary_current_source_set_ready"], False)
        self.assertIs(packet["strict_historical_replay_ready"], False)
        self.assertIs(packet["historical_availability_backdated"], False)
        for boundary in packet["availability_boundaries"]:
            self.assertEqual(set(boundary), {"as_of", "eligible_source_ids"})
            self.assertEqual(boundary["eligible_source_ids"], [])
        validate_replay_lineage_packet(packet=packet, registry=registry)
        for cutoff in ("2026-09-26T12:59:59Z", "2026-09-26T13:01:00Z",
                       "2030-01-01T00:00:00Z"):
            with self.subTest(cutoff=cutoff):
                with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
                    select_replay_members(packet=packet, registry=registry, as_of=cutoff)

    def test_equal_instants_are_deterministic_without_admitting_sources(self):
        for second_time in ("2026-09-26T09:00:00-04:00",
                            "2026-09-26T13:00:00.000000Z"):
            with self.subTest(second_time=second_time):
                registry, record = self.first_slice(second_time)
                original = copy.deepcopy(record)
                packet = self.packet(registry, record)
                self.assertEqual(record, original)
                self.assertEqual(
                    {r["source_id"]: (r["acquired_at"], r["available_at"])
                     for r in original["members"]},
                    {r["source_id"]: (r["acquired_at"], r["available_at"])
                     for r in packet["members"]},
                )
                self.assertEqual(
                    [instant("2026-09-26T13:00:00Z"), instant("2026-09-26T13:01:00Z")],
                    [instant(r["as_of"]) for r in packet["availability_boundaries"]],
                )
                reversed_record = copy.deepcopy(record)
                reversed_record["members"].reverse()
                self.assertEqual(packet, self.packet(registry, reversed_record))
                self.assert_contained(packet, registry)
                equivalent_boundary = copy.deepcopy(packet)
                equivalent_boundary["availability_boundaries"][0]["as_of"] = "2026-09-26T09:00:00-04:00"
                rehash(equivalent_boundary)
                self.assert_contained(equivalent_boundary, registry)
                self.assertEqual(packet["members"], equivalent_boundary["members"])

    def test_complete_boundaries_reject_rehashed_removal_extra_duplicate_and_shift(self):
        registry, record = self.first_slice()
        original = self.packet(registry, record)
        for mutation in ("missing", "extra", "duplicate", "shift"):
            with self.subTest(mutation=mutation):
                packet = copy.deepcopy(original)
                boundaries = packet["availability_boundaries"]
                if mutation == "missing":
                    del boundaries[0]
                elif mutation == "extra":
                    boundaries.insert(1, {"as_of": "2026-09-26T13:00:30Z",
                                          "eligible_source_ids": []})
                elif mutation == "duplicate":
                    boundaries.insert(1, copy.deepcopy(boundaries[0]))
                else:
                    boundaries[0]["as_of"] = "2026-09-26T13:00:30Z"
                rehash(packet)
                with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
                    validate_replay_lineage_packet(packet=packet, registry=registry)
                with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
                    select_replay_members(packet=packet, registry=registry,
                                          as_of="2030-01-01T00:00:00Z")

    def test_release_chronology_is_checked_before_the_final_admission_hold(self):
        registry, record = self.first_slice()
        record["release_created_at"] = "2026-09-26T09:01:00-04:00"
        rebind(record)
        validate_public_materialization_attestation(attestation=record, registry=registry)
        packet = self.packet(registry, record)
        self.assertEqual(packet["release_created_at"], record["release_created_at"])
        self.assert_contained(packet, registry)
        bad_record = copy.deepcopy(record)
        bad_record["release_created_at"] = "2026-09-26T13:00:30Z"
        rebind(bad_record)
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release.*precede"):
            validate_public_materialization_attestation(attestation=bad_record, registry=registry)
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release.*precede"):
            self.packet(registry, bad_record)
        bad_packet = copy.deepcopy(packet)
        bad_packet["release_created_at"] = bad_record["release_created_at"]
        rebind(bad_packet)
        rehash(bad_packet)
        with self.assertRaisesRegex(ReplayLineageError, "release.*precede"):
            validate_replay_lineage_packet(packet=bad_packet, registry=registry)
        with self.assertRaisesRegex(ReplayLineageError, "release.*precede"):
            select_replay_members(packet=bad_packet, registry=registry,
                                  as_of="2030-01-01T00:00:00Z")

    def test_correct_time_grouping_and_hashes_cannot_reopen_admission(self):
        registry, record = self.first_slice()
        packet = self.packet(registry, record)
        claimed = copy.deepcopy(record)
        for member in claimed["members"]:
            member["ordinary_t2_eligible"] = True
        claimed["ordinary_t2_eligible_count"] = len(claimed["members"])
        claimed["ordinary_t2_blocked_count"] = 0
        claimed["all_sources_ordinary_t2_eligible"] = True
        with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
            self.packet(registry, claimed)
        claimed_packet = copy.deepcopy(packet)
        claimed_packet["ordinary_current_source_set_ready"] = True
        rehash(claimed_packet)
        with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
            validate_replay_lineage_packet(packet=claimed_packet, registry=registry)
        claimed_packet = copy.deepcopy(packet)
        claimed_packet["availability_boundaries"][0]["eligible_source_ids"] = ["SRC-A", "SRC-B"]
        rehash(claimed_packet)
        with self.assertRaisesRegex(ReplayLineageError, "eligibility.*empty"):
            validate_replay_lineage_packet(packet=claimed_packet, registry=registry)

    def legacy_generic(self, one=False):
        registry, first = self.first_slice()
        members = copy.deepcopy(first["members"][:1] if one else first["members"])
        sources = []
        for member in members:
            member["ordinary_t2_eligible"] = True
            locator = "https://example.invalid/" + member["source_id"]
            member["source_locator"] = locator
            sources.append({
                "source_id": member["source_id"], "source_version_id": member["source_version_id"],
                "source_locator": locator, "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            })
        attestation = {
            "slice_id": registry["slice_id"], "release_id": first["release_id"],
            "release_sha256": first["release_sha256"],
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "materialized_source_count": len(members), "ordinary_t2_eligible_count": len(members),
            "all_sources_ordinary_t2_eligible": True,
            "historical_availability_backdated": False, "strict_historical_replay_promoted": False,
            "public_raw_content_published": False, "members": members,
        }
        return sources, attestation

    def test_generic_receipt_count_remains_strict_with_legacy_omission(self):
        sources, attestation = self.legacy_generic(one=True)
        def build(value):
            return build_ordinary_t2_lineage(attestation=value, source_records=sources,
                                            expected_slice_id=attestation["slice_id"])
        without_count = build(attestation)
        valid = copy.deepcopy(attestation)
        valid["valid_receipt_count"] = 1
        self.assertEqual(without_count, build(valid))
        for value in (0, 2, True, False, 1.0, "1", None):
            with self.subTest(valid_receipt_count=value):
                bad = copy.deepcopy(attestation)
                bad["valid_receipt_count"] = value
                with self.assertRaisesRegex(OrdinaryT2LineageError, "valid receipt count"):
                    build(bad)

    def test_generic_metadata_retains_exact_transitions_without_canonical_promotion(self):
        sources, attestation = self.legacy_generic()
        source = build_ordinary_t2_lineage(
            attestation=attestation, source_records=sources,
            expected_slice_id=attestation["slice_id"],
        )
        evidence = [{"evidence_id": "EV-" + str(i), "source_id": row["source_id"],
                     "origin_artifact": "synthetic.json", "available_at": None}
                    for i, row in enumerate(sources)]
        args = dict(lineage_packet=source, source_records=sources, evidence_records=evidence,
                    expected_slice_id=attestation["slice_id"])
        bound = build_ordinary_t2_evidence_lineage(**args)
        for label, packet in (("source", source), ("evidence", bound)):
            with self.subTest(label=label):
                self.assertEqual(2, len(packet["availability_boundaries"]))
                self.assertIs(packet["strict_historical_replay_ready"], False)
                self.assertIs(packet["canonical_evidence_admission_promoted"], False)
                bad = copy.deepcopy(packet)
                del bad["availability_boundaries"][0]
                if label == "source":
                    with self.assertRaisesRegex(OrdinaryT2LineageError, "boundary instants"):
                        validate_ordinary_t2_lineage(
                            packet=bad, source_records=sources,
                            expected_slice_id=attestation["slice_id"],
                        )
                else:
                    with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "boundary instants"):
                        validate_ordinary_t2_evidence_lineage(packet=bad, **args)


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows required before any HYDRA import")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if repo.drive.upper() != "D:":
        raise SystemExit("D: candidate checkout required")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo / "constraint-t1-raw-artifact-store" / "src"))
    global ATTESTATION_SCHEMA, FirstSliceMaterializationError
    global validate_public_materialization_attestation
    global ReplayLineageError, build_replay_lineage_packet
    global validate_replay_lineage_packet, select_replay_members, build_release_manifest
    global OrdinaryT2LineageError, build_ordinary_t2_lineage, validate_ordinary_t2_lineage
    global OrdinaryT2EvidenceLineageError, build_ordinary_t2_evidence_lineage
    global validate_ordinary_t2_evidence_lineage
    from hydra_constraint_t1_raw.first_slice_materialization import (
        ATTESTATION_SCHEMA, FirstSliceMaterializationError,
        validate_public_materialization_attestation,
    )
    from hydra_constraint_t1_raw.replay_lineage import (
        ReplayLineageError, build_replay_lineage_packet,
        validate_replay_lineage_packet, select_replay_members,
    )
    from hydra_constraint_t1_raw.store import build_release_manifest
    from hydra_constraint_t1_raw.ordinary_t2_lineage import (
        OrdinaryT2LineageError, build_ordinary_t2_lineage, validate_ordinary_t2_lineage,
    )
    from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (
        OrdinaryT2EvidenceLineageError, build_ordinary_t2_evidence_lineage,
        validate_ordinary_t2_evidence_lineage,
    )
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TemporalCoexistenceTests)
    if args.json_output.resolve().drive.upper() != "D:":
        raise SystemExit("D: reporting output required")
    methods = []
    subtests = []
    class ReportingResult(unittest.TextTestResult):
        def startTest(self, test):
            super().startTest(test)
            methods.append({"nodeid": test.id(), "outcome": "running"})
        def mark(self, test, outcome, detail=None):
            row = next(row for row in reversed(methods) if row["nodeid"] == test.id())
            row["outcome"] = outcome
            if detail is not None: row["detail"] = detail
        def addSuccess(self, test):
            super().addSuccess(test); self.mark(test, "passed")
        def addFailure(self, test, err):
            super().addFailure(test, err); self.mark(test, "failed", self._exc_info_to_string(err, test))
        def addError(self, test, err):
            super().addError(test, err); self.mark(test, "error", self._exc_info_to_string(err, test))
        def addSkip(self, test, reason):
            super().addSkip(test, reason); self.mark(test, "skipped", reason)
        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            outcome = "passed" if err is None else "failed" if issubclass(err[0], test.failureException) else "error"
            subtests.append({"method": test.id(), "subtest_id": subtest.id(), "outcome": outcome,
                             "detail": None if err is None else self._exc_info_to_string(err, test)})
            if err is not None: self.mark(test, outcome)
    result = unittest.TextTestRunner(verbosity=2, resultclass=ReportingResult).run(suite)
    payload = {"tests_run": result.testsRun, "successful": result.wasSuccessful(),
               "methods": methods, "subtests": subtests,
               "method_totals": {outcome: sum(row["outcome"] == outcome for row in methods)
                                 for outcome in ("passed", "failed", "error", "skipped", "running")},
               "subtest_totals": {outcome: sum(row["outcome"] == outcome for row in subtests)
                                  for outcome in ("passed", "failed", "error")}}
    args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if len(methods) != 6 or len({row["nodeid"] for row in methods}) != 6 or any(row["outcome"] == "running" for row in methods):
        raise SystemExit("Incomplete coexistence method accounting")
    if result.skipped or result.testsRun != 6:
        raise SystemExit("All six coexistence methods must execute without skips")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
