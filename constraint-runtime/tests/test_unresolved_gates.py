"""Thread E: synthetic negative cases; no authority or historical evidence is created."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from hydra_constraint import (
    CanonicalEvent, ConstraintRuntime, DeploymentGuard, DurableLedgerRuntime,
    Event, EventNormalizer, EventStore, IngestError, OperationsReport, ReplayHarness,
)
from hydra_constraint.canary import CanaryResponse, CanaryRunner, CanarySpec
from test_v018_runtime import GRAPH, ALIASES


AS_OF = "2026-09-30T00:00:00Z"
UNRESOLVED = {
    "D_OWNER_GATE": "BLOCKED",
    "IMPLEMENTATION_ADMITTED": "NO",
    "PIT_002B": "OPEN",
    "EATON_TIMESTAMP": "TIMESTAMP_UNVERIFIED",
    "GE_VERNOVA_TIMESTAMP": "TIMESTAMP_UNVERIFIED",
    "TRUSTED_TIMESTAMP_VERIFICATION": "NOT_IMPLEMENTED",
    "FULL_TEMPORAL_AUTHORITY_AUDIT": "NOT_RUN",
    "AUTHORIZED_REAL_OUTCOME_EVIDENCE": "NOT_ESTABLISHED_BY_RUNTIME",
}


def raw_event(**changes):
    raw = {
        "event_key": "THREAD-E-SYNTHETIC", "event_type": "material_shortage",
        "target": "Gallium", "occurred_at": "2026-09-29T12:00:00Z",
        "known_at": "2026-09-29T12:01:00Z", "captured_at": "2026-09-29T12:02:00Z",
        "evidence_class": "A1", "severity": 0.8, "jurisdiction": "Global",
        "source_id": "SYNTHETIC-NOT-AUTHORITY", "source_class": "federal_register",
        "source_priority": 100, "details": {},
    }
    raw.update(changes)
    return raw


class UnresolvedGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import hydra_constraint.runtime
        root = Path(hydra_constraint.runtime.__file__).parent
        cls.before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(root.glob("*.py"))}
        print("THREAD_E_SOURCE_HASHES_BEFORE=" + json.dumps(cls.before, sort_keys=True), flush=True)

    @classmethod
    def tearDownClass(cls):
        after = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in cls.before}
        print("THREAD_E_SOURCE_HASHES_AFTER=" + json.dumps(after, sort_keys=True), flush=True)
        if after != cls.before:
            raise AssertionError("runtime source bytes changed during hostile tests")

    def setUp(self):
        self.normalizer = EventNormalizer(GRAPH, aliases=ALIASES)
        self.runtime = ConstraintRuntime.from_dict(GRAPH)
        self.harness = ReplayHarness(self.runtime)

    def assert_hold(self, output):
        self.assertNotEqual(output.get("replay_state"), "CONFIRMED", output)
        self.assertFalse(any(x["state"] == "CONFIRMED" for x in output.get("exposures", [])), output)
        hold = output.get("admission", {})
        self.assertEqual(hold.get("status"), "BLOCKED", output)
        self.assertIs(hold.get("canonical_admission"), False)
        self.assertIs(hold.get("readiness_promotion"), False)
        self.assertEqual(hold.get("gates"), UNRESOLVED)

    def evaluate(self, raw):
        return self.harness.evaluate(self.normalizer.normalize(raw), AS_OF)

    def test_missing_authority_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event()))

    def test_missing_evidence_class_is_blocked(self):
        raw = raw_event()
        del raw["evidence_class"]
        self.assertEqual(self.evaluate(raw)["replay_state"], "BLOCKED")

    def test_malformed_evidence_class_is_rejected(self):
        for value in (True, "PASS", {"status": "A1"}, ["A1"]):
            with self.subTest(value=value), self.assertRaises(IngestError):
                self.normalizer.normalize(raw_event(evidence_class=value))

    def test_malformed_authority_evidence_never_confirms(self):
        for value in (None, True, "PASS", [], {"status": True}):
            with self.subTest(value=value):
                self.assert_hold(self.evaluate(raw_event(details={"authority_evidence": value})))

    def test_unresolved_owner_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"D_OWNER_GATE": "BLOCKED", "owner": None})))

    def test_implementation_not_admitted_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"IMPLEMENTATION_ADMITTED": "NO"})))

    def test_invalid_signature_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"signature_state": "INVALID", "owner": "claimed"})))

    def test_eaton_timestamp_unverified_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(source_id="EATON", details={"timestamp_status": "TIMESTAMP_UNVERIFIED"})))

    def test_ge_vernova_timestamp_unverified_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(source_id="GE_VERNOVA", details={"timestamp_status": "TIMESTAMP_UNVERIFIED"})))

    def test_absent_trusted_timestamp_verification_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"trusted_timestamp_verification": None})))

    def test_absent_full_temporal_authority_audit_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"full_temporal_authority_audit": "NOT_RUN"})))

    def test_absent_authorized_real_outcome_evidence_never_confirms(self):
        self.assert_hold(self.evaluate(raw_event(details={"authorized_real_outcome_evidence": []})))

    def test_timestamp_fallback_is_not_historical_proof(self):
        raw = raw_event(known_at=None, occurred_at=None, source_published_at="2020-01-01T00:00:00Z")
        normalized = self.normalizer.normalize(raw)
        self.assertTrue(any("derived" in note for note in normalized.ingest_notes))
        self.assert_hold(self.harness.evaluate(normalized, AS_OF))

    def test_valid_lineage_with_open_pit_never_confirms(self):
        body = b"synthetic bytes, not historical proof"
        self.assert_hold(self.evaluate(raw_event(details={
            "artifact_sha256": hashlib.sha256(body).hexdigest(),
            "lineage": {"status": "PASS", "source_version_id": "SYNTHETIC-V1"}, "PIT_002B": "OPEN",
        })))

    def test_direct_runtime_cannot_bypass_unresolved_gates(self):
        event = Event("DIRECT", "material_shortage", "MAT_GALLIUM",
                      "2026-09-29T12:00:00Z", "2026-09-29T12:01:00Z", 0.8,
                      details={"D_OWNER_GATE": "BLOCKED", "IMPLEMENTATION_ADMITTED": "NO"})
        out = self.runtime.evaluate_event(event).to_dict()
        self.assertTrue(out["exposures"], "candidate traversal must remain available")
        self.assert_hold(out)

    def test_forged_pass_configuration_cannot_enable_admission(self):
        graph = copy.deepcopy(GRAPH)
        graph["admission"] = {"status": "PASS", "canonical_admission": True}
        graph["runtime_config"] = {"allow_unverified": True, "IMPLEMENTATION_ADMITTED": "YES"}
        graph["edges"][0]["metadata"] = {"authority": "PASS", "signature_state": "VALID"}
        event = Event("FORGED", "material_shortage", "MAT_GALLIUM",
                      "2026-09-29T12:00:00Z", "2026-09-29T12:01:00Z", 0.8,
                      details={"admission": graph["admission"], "ready": True})
        self.assert_hold(ConstraintRuntime.from_dict(graph).evaluate_event(event).to_dict())

    def test_valid_hash_invalid_authority_survives_recovery_without_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            ledger_path, checkpoint = Path(td) / "ledger.jsonl", Path(td) / "checkpoint.json"
            durable = DurableLedgerRuntime(self.normalizer, ledger_path, checkpoint)
            durable.recover()
            durable.ingest_adapted(raw_event(details={"signature_state": "INVALID", "D_OWNER_GATE": "BLOCKED"}))
            self.assertEqual(durable.ledger.verify_chain()["status"], "PASS")
            before_bytes = ledger_path.read_bytes()
            before = durable.ledger.active_events()
            recovered = DurableLedgerRuntime(self.normalizer, ledger_path, checkpoint)
            self.assertEqual(recovered.recover()["chain_status"], "PASS")
            self.assertEqual(before, recovered.ledger.active_events())
            self.assertEqual(before_bytes, ledger_path.read_bytes())
            out = self.harness.evaluate(CanonicalEvent(**before[0]), AS_OF)
            self.assert_hold(out)
            self.assertEqual(before, recovered.ledger.active_events())

    def test_duplicate_source_rank_is_not_authority(self):
        store = EventStore(self.normalizer)
        store.ingest_one(raw_event(evidence_class="B1"))
        incoming = raw_event(details={"signature_state": "INVALID", "IMPLEMENTATION_ADMITTED": "NO"})
        store.ingest_one(incoming)
        self.assert_hold(self.harness.evaluate(store.canonical_events()[0], AS_OF))

    def test_direct_canonical_event_cannot_bypass_hold(self):
        event = self.normalizer.normalize(raw_event())
        event.details = {"canonical_admission": True, "trusted_timestamp_verification": "PASS"}
        self.assert_hold(self.harness.evaluate(event, AS_OF))

    def test_runtime_config_cannot_enable_production(self):
        out = DeploymentGuard.validate({"IMPLEMENTATION_ADMITTED": "YES", "sources": {
            "fixture": {"enabled": True, "live_canary": False, "read_only": False},
        }})
        self.assertEqual(out["status"], "FAIL", out)

    def test_read_only_canary_configuration_keeps_admission_blocked(self):
        out = DeploymentGuard.validate({"sources": {
            "fixture": {"enabled": True, "live_canary": True, "read_only": True},
        }})
        self.assertEqual(out["status"], "PASS")
        self.assert_hold(out)

    def test_operational_pass_is_not_readiness(self):
        out = OperationsReport.build(
            freshness=[{"source": "fixture", "health": "HEALTHY"}],
            drift=[{"source": "fixture", "status": "PASS"}],
            failure_state={"sources": {"fixture": {"state": "HEALTHY"}}},
            ledger_recovery={"status": "PASS", "chain_status": "PASS"},
            golden={"status": "PASS"}, deployment={"status": "PASS"})
        self.assertEqual(out["status"], "PASS")
        self.assert_hold(out)

    def test_unknown_or_empty_monitoring_is_not_pass(self):
        for freshness in ([], [{"source": "fixture", "health": "UNKNOWN"}]):
            with self.subTest(freshness=freshness):
                out = OperationsReport.build(freshness=freshness, drift=[], failure_state={},
                    ledger_recovery={"status": "PASS"}, golden={"status": "PASS"}, deployment={"status": "PASS"})
                self.assertNotEqual(out["status"], "PASS", out)

    def test_canary_success_is_not_historical_proof(self):
        class FakeTransport:
            def fetch(self, spec, user_agent):
                return CanaryResponse(200, spec.url, {}, b"fixture marker")
        out = CanaryRunner(FakeTransport()).run([CanarySpec("fixture", "https://example.test", ["marker"])])
        self.assertEqual(out["status"], "PASS")
        self.assertFalse(out["ledger_mutation"])
        self.assert_hold(out)


if __name__ == "__main__":
    unittest.main()
