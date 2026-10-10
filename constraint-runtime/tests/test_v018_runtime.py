from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint import (
    AppendOnlyEventLedger,
    BackoffPolicy,
    ConstraintRuntime,
    CursorStore,
    DeploymentGuard,
    DriftGuard,
    DurableLedgerRuntime,
    Event,
    EventNormalizer,
    EventStore,
    EvidenceClass,
    ExposureState,
    IngestError,
    ReplayHarness,
)
from hydra_constraint.polling import FixtureTransport, HttpResponse, PollRunner, PollSpec, RawArchive
from hydra_constraint.runtime import Node, Edge


GRAPH = {
    "nodes": [
        {"node_id":"MAT_GALLIUM","node_class":"material","name":"Gallium","lifecycle_state":"operating","jurisdiction":"Global",
         "concentration":{"production":99,"processing":95},"substitution":{"technical":22,"qualification":23,"logistics":12,"lead_time":22}},
        {"node_id":"COMP_GAN","node_class":"component","name":"GaN device class","lifecycle_state":"operating","jurisdiction":"Global"},
        {"node_id":"CO_NVIDIA","node_class":"company","name":"NVIDIA","lifecycle_state":"operating","jurisdiction":"United States"},
        {"node_id":"PORT_LA","node_class":"port","name":"Port of Los Angeles","lifecycle_state":"operating","jurisdiction":"United States"},
        {"node_id":"FAC_FAB","node_class":"facility","name":"Example Fab","lifecycle_state":"operating","jurisdiction":"United States"},
        {"node_id":"FAC_FUTURE","node_class":"facility","name":"Future Fab","lifecycle_state":"buildout","operational_from":"2030-01-01T00:00:00Z","jurisdiction":"United States"},
    ],
    "edges": [
        {"edge_id":"E_GA_GAN","from_node":"MAT_GALLIUM","to_node":"COMP_GAN","relationship":"FEEDS","evidence_class":"A1"},
        {"edge_id":"E_GAN_NVDA","from_node":"COMP_GAN","to_node":"CO_NVIDIA","relationship":"SECTOR_EXPOSURE","evidence_class":"C",
         "guardrail":"generic device class does not prove a named company BOM"},
        {"edge_id":"E_PORT_FAB","from_node":"PORT_LA","to_node":"FAC_FAB","relationship":"OBSERVED_GATEWAY","evidence_class":"B1",
         "semantics":"observed_route","impact_scope":"logistics","guardrail":"observed gateway is non-exclusive"},
        {"edge_id":"E_FAB_NVDA","from_node":"FAC_FAB","to_node":"CO_NVIDIA","relationship":"SITE_PRODUCT","evidence_class":"OPEN"},
        {"edge_id":"E_GA_FUTURE","from_node":"MAT_GALLIUM","to_node":"FAC_FUTURE","relationship":"REQUIRES","evidence_class":"A1",
         "impact_scope":"production"},
    ],
}

ALIASES = {
    "Gallium":"MAT_GALLIUM",
    "NVIDIA":"CO_NVIDIA",
    "Port of Los Angeles":"PORT_LA",
    "Example Fab":"FAC_FAB",
}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ConstraintRuntime.from_dict(GRAPH)

    def test_a1_can_propagate_but_c_named_company_is_blocked(self):
        out = self.runtime.evaluate_event(Event(
            "EV1","material_export_control","MAT_GALLIUM",
            "2026-09-29T12:00:00Z","2026-09-29T12:01:00Z",0.9
        ))
        self.assertIn("COMP_GAN", {x.node_id for x in out.exposures})
        self.assertNotIn("CO_NVIDIA", {x.node_id for x in out.exposures})
        self.assertTrue(any(x.edge_id == "E_GAN_NVDA" for x in out.blocked_hops))

    def test_observed_route_is_candidate(self):
        out = self.runtime.evaluate_event(Event(
            "EV2","port_delay","PORT_LA",
            "2026-09-29T12:00:00Z","2026-09-29T12:01:00Z",0.8
        ))
        fab = next(x for x in out.exposures if x.node_id == "FAC_FAB")
        self.assertEqual(fab.state, "CANDIDATE")

    def test_future_production_is_deferred(self):
        out = self.runtime.evaluate_event(Event(
            "EV3","material_shortage","MAT_GALLIUM",
            "2026-09-29T12:00:00Z","2026-09-29T12:01:00Z",0.9
        ))
        self.assertNotIn("FAC_FUTURE", {x.node_id for x in out.exposures})
        self.assertTrue(any(x.edge_id == "E_GA_FUTURE" for x in out.deferred_hops))

    def test_no_auto_trading_signal(self):
        out = self.runtime.evaluate_event(Event(
            "EV4","material_shortage","MAT_GALLIUM",
            "2026-09-29T12:00:00Z","2026-09-29T12:01:00Z",0.5
        ))
        self.assertTrue(out.no_auto_trading_signal)


class EventTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = EventNormalizer(GRAPH, aliases=ALIASES)
        self.harness = ReplayHarness(ConstraintRuntime.from_dict(GRAPH))

    def test_rumor_is_capped_and_blocked(self):
        ev = self.normalizer.normalize({
            "headline":"rumor","event_key":"R1","event_type":"facility_outage",
            "target":"Example Fab","occurred_at":"2026-09-29T12:00:00Z",
            "known_at":"2026-09-29T12:01:00Z","captured_at":"2026-09-29T12:02:00Z",
            "evidence_class":"A1","severity":1.0,"jurisdiction":"United States","record_status":"rumor",
        })
        self.assertEqual(ev.evidence_class, "C")
        self.assertEqual(self.harness.evaluate(ev,"2026-09-29T13:00:00Z")["replay_state"], "BLOCKED")

    def test_future_effective_event_is_pending(self):
        ev = self.normalizer.normalize({
            "headline":"rule","event_key":"P1","event_type":"material_export_control",
            "target":"Gallium","occurred_at":"2026-09-29T12:00:00Z",
            "known_at":"2026-09-29T12:01:00Z","effective_at":"2026-10-15T00:00:00Z",
            "captured_at":"2026-09-29T12:02:00Z","evidence_class":"A1","severity":0.8,"jurisdiction":"Global",
        })
        self.assertEqual(self.harness.evaluate(ev,"2026-09-30T00:00:00Z")["replay_state"], "PENDING_EFFECTIVE")

    def test_wrong_jurisdiction_rejected(self):
        with self.assertRaises(IngestError):
            self.normalizer.normalize({
                "event_type":"facility_outage","target":"Example Fab",
                "captured_at":"2026-09-29T12:00:00Z","evidence_class":"A1","severity":1.0,
                "jurisdiction":"China",
            })

    def test_duplicate_headlines_merge(self):
        store = EventStore(self.normalizer)
        base = {
            "event_key":"D1","event_type":"port_delay","target":"Port of Los Angeles",
            "occurred_at":"2026-09-29T12:00:00Z","known_at":"2026-09-29T12:01:00Z",
            "captured_at":"2026-09-29T12:02:00Z","evidence_class":"A1","severity":0.5,
            "jurisdiction":"United States","source_id":"A",
        }
        a = dict(base, headline="first")
        b = dict(base, headline="rewritten", source_id="B", captured_at="2026-09-29T12:03:00Z")
        self.assertEqual(store.ingest_one(a).disposition, "ACCEPTED_NEW")
        self.assertEqual(store.ingest_one(b).disposition, "DUPLICATE_MERGED")
        self.assertEqual(len(store.events), 1)


class LedgerPersistenceTests(unittest.TestCase):
    def test_lower_authority_cannot_overwrite_official_and_chain_passes(self):
        normalizer = EventNormalizer(GRAPH, aliases=ALIASES)
        ledger = AppendOnlyEventLedger(normalizer)
        official = {
            "headline":"official","event_key":"X1","event_type":"material_export_control","target":"Gallium",
            "occurred_at":"2026-09-29T12:00:00Z","known_at":"2026-09-29T12:01:00Z",
            "effective_at":"2026-10-15T00:00:00Z","captured_at":"2026-09-29T12:02:00Z",
            "source_id":"OFFICIAL","source_class":"federal_register","source_priority":100,
            "external_record_id":"X1","evidence_class":"A1","severity":0.8,"jurisdiction":"Global",
        }
        low = dict(official, effective_at="2026-10-01T00:00:00Z",
                   captured_at="2026-09-29T13:00:00Z",source_id="LOW",
                   source_class="secondary_report",source_priority=40,external_record_id="LOW")
        ledger.ingest_adapted(official)
        entry = ledger.ingest_adapted(low)
        self.assertEqual(entry.action, "QUARANTINE")
        self.assertEqual(ledger.active_events()[0]["effective_at"], "2026-10-15T00:00:00Z")
        self.assertEqual(ledger.verify_chain()["status"], "PASS")

    def test_restart_recovers_same_tip(self):
        normalizer = EventNormalizer(GRAPH, aliases=ALIASES)
        raw = {
            "headline":"official","event_key":"X2","event_type":"material_export_control","target":"Gallium",
            "occurred_at":"2026-09-29T12:00:00Z","known_at":"2026-09-29T12:01:00Z",
            "effective_at":"2026-10-15T00:00:00Z","captured_at":"2026-09-29T12:02:00Z",
            "source_id":"OFFICIAL","source_class":"federal_register","source_priority":100,
            "external_record_id":"X2","evidence_class":"A1","severity":0.8,"jurisdiction":"Global",
        }
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            one = DurableLedgerRuntime(normalizer, td/"ledger.jsonl", td/"checkpoint.json")
            one.recover()
            entry = one.ingest_adapted(raw)
            two = DurableLedgerRuntime(EventNormalizer(GRAPH,aliases=ALIASES), td/"ledger.jsonl", td/"checkpoint.json")
            report = two.recover()
            self.assertEqual(report["ledger_tip_hash"], entry.entry_hash)
            self.assertEqual(report["chain_status"], "PASS")


class PollRunnerTests(unittest.TestCase):
    def test_partial_batch_keeps_successes_idempotent_and_retries_bad_record(self):
        normalizer = EventNormalizer(GRAPH, aliases=ALIASES)
        url = "https://fixture.invalid/sec"
        rows = [
            {"accession_number":"0000000001-26-000001","filing_date":"2026-09-29","company":"Example A","form":"8-K","cik":"1","url":url},
            {"filing_date":"2026-09-29","company":"Malformed","form":"8-K","cik":"2","url":url},
            {"accession_number":"0000000002-26-000002","filing_date":"2026-09-29","company":"Example B","form":"8-K","cik":"3","url":url},
        ]
        body = json.dumps({"records":rows}).encode("utf-8")
        response = HttpResponse(url,200,{"etag":"fixture-v1"},body,"2026-09-29T12:02:00Z")

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            durable = DurableLedgerRuntime(normalizer,td/"ledger.jsonl",td/"checkpoint.json")
            durable.recover()
            cursors = CursorStore(td/"cursor.json")
            runner = PollRunner(
                durable,cursors,RawArchive(td/"raw"),FixtureTransport({url:[response]})
            )
            spec = PollSpec(
                name="sec_fixture",adapter="sec_edgar",source_class="sec_edgar",
                url=url,parser="json_records",cadence_minutes=60,stale_after_minutes=180,
                target="Gallium",jurisdiction="Global",
            )

            first = runner.poll(spec)
            first_entry_count = len(durable.ledger.entries)
            self.assertEqual(first.status,"APPEND_FAILED")
            self.assertEqual(first.appended,2)
            self.assertEqual(first.cursor_after,None)
            self.assertIn("record[1]",first.error)
            self.assertIn("accession_number",first.error)
            self.assertTrue(cursors.has_seen("sec_fixture","000000000126000001"))
            self.assertTrue(cursors.has_seen("sec_fixture","000000000226000002"))
            self.assertEqual(len(durable.ledger.entries),2)

            second = runner.poll(spec)
            self.assertEqual(second.status,"APPEND_FAILED")
            self.assertEqual(second.appended,0)
            self.assertEqual(second.skipped_seen,2)
            self.assertEqual(len(durable.ledger.entries),first_entry_count)
            self.assertEqual(
                [entry.action for entry in durable.ledger.entries],
                ["CREATE","CREATE"],
            )
            self.assertIsNone(cursors.adapter("sec_fixture")["cursor"])
            self.assertIsNone(cursors.adapter("sec_fixture")["last_success_at"])
            self.assertIn("record[1]",cursors.adapter("sec_fixture")["last_error"])
            self.assertEqual(
                [entry.external_record_id for entry in durable.ledger.entries],
                ["000000000126000001","000000000226000002"],
            )


class OperationsTests(unittest.TestCase):
    def test_schema_drift_freezes(self):
        contracts = {"sec":{"required_root_keys":["cik","name","filings"],"required_recent_keys":["form"]}}
        guard = DriftGuard(contracts)
        result = guard.inspect("sec","sec_json",b'{"cik":"1","filings":{"recent":{}}}')
        self.assertEqual(result.status, "FROZEN")

    def test_failure_budget_freezes_and_recovers(self):
        budget = __import__("hydra_constraint").FailureBudget()
        self.assertEqual(budget.update("x",False)["state"], "HEALTHY")
        self.assertEqual(budget.update("x",False)["state"], "WARN")
        self.assertEqual(budget.update("x",False)["state"], "FROZEN")
        self.assertEqual(budget.update("x",True)["state"], "FROZEN")
        self.assertEqual(budget.update("x",True)["state"], "HEALTHY")

    def test_enabled_sec_placeholder_is_rejected(self):
        config = {"sources":{"sec_nvidia":{
            "enabled":True,"live_canary":True,"read_only":True,"user_agent":"REPLACE_WITH_REAL_CONTACT"
        }}}
        self.assertEqual(DeploymentGuard.validate(config)["status"], "FAIL")

    def test_backoff_is_bounded(self):
        policy = BackoffPolicy(max_attempts=5,base_seconds=2,cap_seconds=5)
        self.assertEqual([policy.delay(i) for i in range(1,5)],[2,4,5,5])


if __name__ == "__main__":
    unittest.main()
