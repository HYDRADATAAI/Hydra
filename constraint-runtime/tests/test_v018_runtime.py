from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import tempfile
import threading
import unittest
from pathlib import Path

from hydra_constraint import (
    AppendOnlyEventLedger,
    BackoffPolicy,
    ConstraintRuntime,
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
from hydra_constraint.runtime import Node, Edge
from hydra_constraint.polling import HttpResponse, PollRunner, PollSpec


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
        policy = BackoffPolicy(max_attempts=5, base_seconds=2, cap_seconds=5)
        self.assertEqual([policy.delay(i) for i in range(1, 5)], [2, 4, 5, 5])
        self.assertEqual(policy.delay(1, "120"), 5)
        self.assertEqual(policy.delay(1, "9" * 1000), 5)
        for malformed in ("malformed", "NaN", "inf", "-inf", "-1", "1.5", "1e3"):
            with self.subTest(retry_after=malformed):
                self.assertEqual(policy.delay(2, malformed), 4)

    def test_backoff_parses_http_date_retry_after(self):
        policy = BackoffPolicy(max_attempts=5, base_seconds=2, cap_seconds=30)
        now = datetime(2015, 10, 21, 7, 28, 0, tzinfo=timezone.utc)

        self.assertEqual(
            policy.delay(2, "Wed, 21 Oct 2015 07:28:10 GMT", now=now),
            10,
        )
        self.assertEqual(
            policy.delay(2, "Wed, 21 Oct 2015 07:29:00 GMT", now=now),
            30,
        )
        self.assertEqual(
            policy.delay(2, "Wed, 21 Oct 2015 07:27:00 GMT", now=now),
            0,
        )
        self.assertEqual(
            policy.delay(2, "Wed, 21 Oct 2015 07:28:10 +0200", now=now),
            4,
        )
        self.assertEqual(
            policy.delay(2, "Tue, 21 Oct 2015 07:28:10 GMT", now=now),
            4,
        )
        self.assertEqual(
            policy.delay(2, "Wed, 21 Oct 2015 07:28:60 GMT", now=now),
            4,
        )
        self.assertEqual(
            policy.delay(2, "Wednesday, 21-Oct-15 07:28:10 GMT", now=now),
            10,
        )
        future_now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
        self.assertEqual(
            policy.delay(2, "Tuesday, 21-Oct-70 07:28:10 GMT", now=future_now),
            30,
        )
        self.assertEqual(
            policy.delay(2, "Friday, 31-Dec-76 23:59:59 GMT", now=future_now),
            0,
        )
        self.assertEqual(
            policy.delay(2, "Wed Oct 21 07:28:10 2015", now=now),
            10,
        )
        asctime_now = datetime(1994, 11, 1, 8, 49, 27, tzinfo=timezone.utc)
        self.assertEqual(
            policy.delay(2, "Tue Nov 01 08:49:37 1994", now=asctime_now),
            10,
        )
        leap_second_now = datetime(2016, 12, 31, 23, 59, 50, tzinfo=timezone.utc)
        self.assertEqual(
            policy.delay(2, "Sat, 31 Dec 2016 23:59:60 GMT", now=leap_second_now),
            10,
        )


class PollRateLimitTests(unittest.TestCase):
    class FakeClock:
        def __init__(self):
            self.now=0.0
            self.delays=[]
        def monotonic(self):
            return self.now
        def sleep(self,seconds):
            self.delays.append(seconds)
            self.now+=seconds

    class BlockingClock(FakeClock):
        def __init__(self):
            super().__init__()
            self.sleep_started=threading.Event()
            self.release_sleep=threading.Event()
        def sleep(self,seconds):
            self.delays.append(seconds)
            self.sleep_started.set()
            if not self.release_sleep.wait(timeout=5):
                raise TimeoutError("fixture cooldown was not released")
            self.now+=seconds

    class TrackingLock:
        def __init__(self):
            self.lock=threading.Lock()
            self.contended=threading.Event()
        def __enter__(self):
            if not self.lock.acquire(blocking=False):
                self.contended.set()
                self.lock.acquire()
            return self
        def __exit__(self,*args):
            self.lock.release()

    class FakeCursors:
        max_seen=10
        path=Path("unused")
        state={}
        def __init__(self):
            self.reads=0
        def adapter(self,name):
            self.reads+=1
            return {"cursor":None}
        def mark_error(self,*args,**kwargs):
            pass

    class FakeArchive:
        def archive(self,source,response,attempt):
            return "fixture-hash"

    class FakeTransport:
        def __init__(self,clock,retry_after=None,latency=0.0,fail_first=False):
            self.clock=clock
            self.retry_after=retry_after
            self.latency=latency
            self.fail_first=fail_first
            self.request_times=[]
        def fetch(self,url,headers=None,timeout=20):
            self.request_times.append(self.clock.monotonic())
            self.clock.now+=self.latency
            if self.fail_first and len(self.request_times)==1:
                raise OSError("fixture transport failure")
            headers={"retry-after":str(self.retry_after)} if self.retry_after is not None else {}
            return HttpResponse(url,503,headers,b"retry","2026-10-09T12:00:00Z")

    def make_spec(self,**kwargs):
        backoff=kwargs.pop("backoff",BackoffPolicy(max_attempts=2,base_seconds=0.1,cap_seconds=2))
        return PollSpec(
            name="sec",adapter="sec_edgar",source_class="sec_edgar",url="https://www.sec.gov/data",
            parser="sec_json",cadence_minutes=1,stale_after_minutes=5,
            backoff=backoff,**kwargs
        )

    def test_retry_attempts_respect_rate_interval(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )

        report=runner.poll(self.make_spec(max_rps=2))

        self.assertEqual(report.status,"FAILED")
        self.assertEqual(transport.request_times,[0.0,0.5])
        self.assertEqual(clock.delays,[0.1,0.4])

    def test_long_retry_after_is_not_added_to_rate_wait(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock,retry_after=1)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )

        runner.poll(self.make_spec(max_rps=2))

        self.assertEqual(transport.request_times,[0.0,1.0])
        self.assertEqual(clock.delays,[1.0])

    def test_final_retry_after_cooldown_applies_to_later_poll(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock,retry_after=2)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )
        spec=self.make_spec(max_rps=2,backoff=BackoffPolicy(max_attempts=1))

        self.assertEqual(runner.poll(spec).status,"FAILED")
        runner.poll(spec)

        self.assertEqual(transport.request_times,[0.0,2.0])
        self.assertEqual(clock.delays,[2.0])

    def test_final_transport_failure_backoff_applies_to_later_poll(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock,fail_first=True)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )
        spec=self.make_spec(
            max_rps=10,backoff=BackoffPolicy(max_attempts=1,base_seconds=0.75,cap_seconds=2)
        )

        self.assertEqual(runner.poll(spec).status,"FAILED")
        runner.poll(spec)

        self.assertEqual(transport.request_times,[0.0,0.75])
        self.assertEqual(clock.delays,[0.75])

    def test_slow_request_does_not_get_an_extra_rate_wait(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock,latency=0.8)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )

        runner.poll(self.make_spec(max_rps=2))

        self.assertEqual(transport.request_times,[0.0,0.9])
        self.assertEqual(clock.delays,[0.1])

    def test_transport_exception_retry_respects_rate_interval(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock,fail_first=True)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )

        runner.poll(self.make_spec(max_rps=2))

        self.assertEqual(transport.request_times,[0.0,0.5])
        self.assertEqual(clock.delays,[0.1,0.4])

    def test_concurrent_polls_for_same_source_share_the_limit(self):
        clock=self.FakeClock()
        transport=self.FakeTransport(clock)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )
        start=threading.Barrier(3)
        spec=self.make_spec(max_rps=2)
        def run_poll():
            start.wait()
            runner.poll(spec)
        threads=[threading.Thread(target=run_poll) for _ in range(2)]
        for thread in threads:
            thread.start()
        start.wait()
        for thread in threads:
            thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        request_times=sorted(transport.request_times)
        self.assertEqual(len(request_times),4)
        self.assertTrue(all(later-earlier>=0.5 for earlier,later in zip(request_times,request_times[1:])))

    def test_concurrent_poll_waits_for_shared_retry_after_cooldown(self):
        clock=self.BlockingClock()
        transport=self.FakeTransport(clock,retry_after=2)
        runner=PollRunner(
            durable=None,cursors=self.FakeCursors(),archive=self.FakeArchive(),transport=transport,
            sleeper=clock,clock=clock.monotonic,
        )
        tracked_lock=self.TrackingLock()
        runner._poll_lock=tracked_lock
        spec=self.make_spec(max_rps=2)
        first=threading.Thread(target=runner.poll,args=(spec,))
        def run_second_poll():
            runner.poll(spec)
        first.start()
        self.assertTrue(clock.sleep_started.wait(timeout=5))
        second=threading.Thread(target=run_second_poll)
        second.start()
        self.assertTrue(tracked_lock.contended.wait(timeout=5))
        self.assertEqual(len(transport.request_times),1)
        clock.release_sleep.set()
        first.join(timeout=5)
        second.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in (first,second)))
        self.assertEqual(len(transport.request_times),4)
        self.assertGreaterEqual(min(transport.request_times[1:]),2.0)

    def test_http_date_retry_cooldown_applies_to_later_poll(self):
        clock = self.FakeClock()
        transport = self.FakeTransport(
            clock,
            retry_after="Wed, 21 Oct 2015 07:28:10 GMT",
        )
        now = datetime(2015, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
        runner = PollRunner(
            durable=None,
            cursors=self.FakeCursors(),
            archive=self.FakeArchive(),
            transport=transport,
            sleeper=clock,
            clock=clock.monotonic,
            wall_clock=lambda: now,
        )
        spec = self.make_spec(
            max_rps=100,
            backoff=BackoffPolicy(max_attempts=1, base_seconds=0.1, cap_seconds=30),
        )

        self.assertEqual(runner.poll(spec).status, "FAILED")
        runner.poll(spec)

        self.assertEqual(transport.request_times, [0.0, 10.0])
        self.assertEqual(clock.delays, [10.0])

    def test_invalid_rate_fails_before_cursor_access(self):
        cursors=self.FakeCursors()
        runner=PollRunner(
            durable=None,cursors=cursors,archive=self.FakeArchive(),
            transport=self.FakeTransport(self.FakeClock()),
        )

        for rate in (True,0,-1,float("inf"),float("nan"),5e-324,10**1000,"1"):
            with self.subTest(rate=rate),self.assertRaisesRegex(ValueError,"max_rps"):
                runner.poll(self.make_spec(max_rps=rate))
        self.assertEqual(cursors.reads,0)


if __name__ == "__main__":
    unittest.main()
