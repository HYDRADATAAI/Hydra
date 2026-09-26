import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hydra_constraint_physical import (
    DependencyGraph, Edge, Node, Provenance as PhysicalProvenance, Snapshot,
    load_sourced_policy_case_graph, validate_graph,
)
from hydra_constraint_policy.case_studies import (
    events_from_sourced_case_bundle, load_sourced_case_bundle,
)
from hydra_constraint_policy.claims import (
    ClaimEvidence, ClaimStance, ClaimState, ContestedClaim, claim_state_as_of,
)
from hydra_constraint_policy.model import (
    EventType, HistoricalEvent, Provenance, Relation, TemporalFacts,
    active_events_as_of, eligible_as_of,
)
from hydra_constraint_policy.physical_adapter import (
    bind_event_to_physical_graph, trace_event_downstream,
)
from hydra_constraint_policy.replay_adapter import to_replay_evidence
from hydra_constraint_replay.models import Hypothesis, Outcome, ReplayCase
from hydra_constraint_replay.replay import replay_case


ROOT=Path(__file__).resolve().parents[2]
POLICY_DATA=ROOT/"constraint-geopolitical-policy"/"data"/"sourced_historical_cases.json"
PHYSICAL_DATA=ROOT/"constraint-physical-dependency"/"data"/"sourced_policy_case_physical_graph.json"
UTC=timezone.utc


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z","+00:00"))


def pp(source_id: str="synthetic-fixture") -> PhysicalProvenance:
    return PhysicalProvenance(
        source_id,
        f"https://example.invalid/{source_id}",
        "synthetic fixture",
        date(2026,9,25),
        date(2019,1,1),
        evidence_hash=f"sha256:{source_id}",
    )


def synthetic_policy_event(
    event_id: str,
    known_at: datetime,
    effective_at: datetime,
    relations: tuple[Relation,...],
    resolved_at: datetime | None=None,
) -> HistoricalEvent:
    p=Provenance(
        "synthetic-fixture",
        f"{event_id}:doc",
        known_at,
        known_at,
        "fixture-v1",
        f"sha256:{event_id}",
    )
    event=HistoricalEvent(
        event_id=event_id,
        event_type=EventType.SHIPPING_DISRUPTION,
        title=event_id,
        temporal=TemporalFacts(
            known_at=known_at,
            effective_at=effective_at,
            observed_at=known_at,
            resolved_at=resolved_at,
        ),
        provenance=(p,),
        relations=relations,
        statement="Synthetic closure fixture; not production historical evidence.",
        metadata={
            "synthetic_fixture":True,
            "source_uris":{p.document_id:f"https://example.invalid/{event_id}"},
        },
    )
    event.validate()
    return event


class LilyDomainReconciliationClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sourced_bundle=load_sourced_case_bundle(POLICY_DATA)
        cls.sourced_events=events_from_sourced_case_bundle(cls.sourced_bundle)
        cls.sourced_graph=load_sourced_policy_case_graph(PHYSICAL_DATA)

    def test_case_b_suez_sourced_chain_reaches_replay_and_resolves(self):
        event=next(
            e for e in self.sourced_events
            if e.event_id=="suez-grounding-disruption-known-2021-03-26"
        )
        bindings=bind_event_to_physical_graph(event,self.sourced_graph)
        self.assertTrue(any(b.entity_id=="infrastructure:suez-canal" for b in bindings))

        traced=trace_event_downstream(event,self.sourced_graph)
        self.assertIn(
            ("edge:suez-canal-supplies-maritime-traffic",),
            traced["infrastructure:suez-canal"],
        )

        evidence=to_replay_evidence(event)
        replay=ReplayCase(
            case_id="sourced-suez-2021-closure",
            replay_t=dt("2021-03-26T00:00:00Z"),
            hypothesis=Hypothesis(
                "suez-maritime-disruption",
                .5,
                "canal disruption reduces maritime throughput",
                "tightening",
                geography=("Suez Canal",),
                infrastructure=("infrastructure:suez-canal",),
                affected_entities=("transport:maritime-traffic-via-suez",),
            ),
            evidence=evidence,
            outcome=Outcome(
                "TRUE_POSITIVE",
                True,
                dt("2021-03-31T00:00:00Z"),
            ),
        )
        result=replay_case(replay)
        self.assertEqual("TRUE_POSITIVE",result["outcome_class"])
        self.assertEqual(len(evidence),result["evidence_count"])

        self.assertIn(
            event,
            active_events_as_of([event],dt("2021-03-30T00:00:00Z")),
        )
        self.assertNotIn(
            event,
            active_events_as_of([event],dt("2021-03-31T00:00:00Z")),
        )
        self.assertIsNone(
            self.sourced_graph.resolve_reference(
                "bottleneck:suez-canal-grounding-2021",
                date(2021,4,1),
                date(2021,4,1),
            )
        )

    def test_case_a_synthetic_resource_chain_is_pit_safe_through_replay(self):
        p=pp("case-a")
        nodes=[
            Node(
                "deposit:a","deposit_source","Deposit A",
                snapshots=(
                    Snapshot(
                        date(2018,1,1),
                        known_at=date(2019,1,1),
                        attributes={"reserve_estimate":80},
                    ),
                    Snapshot(
                        date(2018,1,1),
                        known_at=date(2022,1,1),
                        attributes={"reserve_estimate":120},
                    ),
                ),
                provenance=(p,),
            ),
            Node("extract:a","extraction","Mine A",provenance=(p,)),
            Node("process:a","processing","Processor A",provenance=(p,)),
            Node("transport:a","transport","Rail A",provenance=(p,)),
            Node("infra:a","infrastructure","Port A",provenance=(p,)),
            Node("company:a","company","Downstream A",provenance=(p,)),
            Node("product:a","product_technology","Product A",provenance=(p,)),
            Node("substitute:a","substitute","Alternate processor",provenance=(p,)),
        ]
        edges=[
            Edge("a1","deposit:a","extract:a","extracted_by",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a2","extract:a","process:a","feeds",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a3","process:a","transport:a","transported_via",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a4","transport:a","infra:a","depends_on",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a5","infra:a","company:a","supplies",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a6","company:a","product:a","manufactures",date(2018,1,1),known_at=date(2019,1,1),provenance=(p,)),
            Edge("a7","process:a","substitute:a","substitutable_by",date(2018,1,1),known_at=date(2019,1,1),substitution_time_days=180,provenance=(p,)),
        ]
        graph=DependencyGraph(nodes,edges)
        self.assertEqual([],validate_graph(graph))

        view=graph.as_of(date(2020,1,1),date(2020,1,1))
        self.assertEqual(1,len(view.nodes["deposit:a"].snapshots))
        self.assertEqual(80,view.nodes["deposit:a"].snapshots[0].attributes["reserve_estimate"])
        self.assertTrue(any(path[-1].target_id=="product:a" for path in view.trace("deposit:a")))
        self.assertEqual(180,view.substitutes("process:a")[0].substitution_time_days)

        event=synthetic_policy_event(
            "synthetic-case-a-disruption",
            dt("2020-01-01T12:00:00Z"),
            dt("2020-01-02T00:00:00Z"),
            (Relation("INFRASTRUCTURE","infra:a",1.0,("synthetic-case-a-disruption:doc",)),),
        )
        bind_event_to_physical_graph(event,graph)
        evidence=to_replay_evidence(event)
        result=replay_case(ReplayCase(
            "synthetic-fixture-case-a",
            dt("2020-01-03T00:00:00Z"),
            Hypothesis(
                "synthetic-case-a-capacity-loss",
                .5,
                "infrastructure disruption reaches downstream product",
                "tightening",
                resources=("deposit:a",),
                infrastructure=("infra:a",),
                affected_entities=("company:a","product:a"),
            ),
            evidence,
            Outcome("PARTIAL_REALIZATION",True,dt("2020-01-10T00:00:00Z")),
        ))
        self.assertEqual("PARTIAL_REALIZATION",result["outcome_class"])
        self.assertTrue(event.metadata["synthetic_fixture"])

    def test_case_c_synthetic_water_energy_capacity_chain_expires_stale_edges(self):
        p=pp("case-c")
        nodes=[
            Node("resource:water","resource","Industrial water",provenance=(p,)),
            Node("infra:water","infrastructure","Water system",provenance=(p,)),
            Node("infra:power","infrastructure","Power system",provenance=(p,)),
            Node("mfg:cluster","manufacturing","Industrial cluster",provenance=(p,)),
            Node("company:c","company","Company C",provenance=(p,)),
            Node("product:c","product_technology","Product C",provenance=(p,)),
        ]
        edges=[
            Edge("c1","resource:water","infra:water","supplies",date(2020,1,1),known_at=date(2020,1,1),provenance=(p,)),
            Edge("c2","infra:water","mfg:cluster","supplies",date(2020,1,1),date(2020,6,1),known_at=date(2020,1,1),provenance=(p,)),
            Edge("c3","infra:power","mfg:cluster","supplies",date(2020,1,1),known_at=date(2020,1,1),provenance=(p,)),
            Edge("c4","mfg:cluster","company:c","supplies",date(2020,1,1),known_at=date(2020,1,1),provenance=(p,)),
            Edge("c5","company:c","product:c","manufactures",date(2020,1,1),known_at=date(2020,1,1),provenance=(p,)),
        ]
        graph=DependencyGraph(nodes,edges)
        self.assertEqual([],validate_graph(graph))
        self.assertIn("product:c",graph.loss_impact("resource:water"))
        self.assertEqual(
            "PRESENT",
            graph.reference_state_as_of("c2",date(2020,5,1),date(2020,5,1)),
        )
        self.assertEqual(
            "ABSENT",
            graph.reference_state_as_of("c2",date(2020,6,2),date(2020,6,2)),
        )
        post=graph.as_of(date(2020,6,2),date(2020,6,2))
        self.assertNotIn("c2",post.edges)

    def test_policy_known_effective_resolved_clocks_do_not_collapse(self):
        event=synthetic_policy_event(
            "synthetic-clock-event",
            dt("2020-01-01T00:00:00Z"),
            dt("2020-02-01T00:00:00Z"),
            (),
            resolved_at=dt("2020-03-01T00:00:00Z"),
        )
        self.assertIn(event,eligible_as_of([event],dt("2020-01-15T00:00:00Z")))
        self.assertNotIn(event,active_events_as_of([event],dt("2020-01-15T00:00:00Z")))
        self.assertIn(event,active_events_as_of([event],dt("2020-02-15T00:00:00Z")))
        self.assertNotIn(event,active_events_as_of([event],dt("2020-03-01T00:00:00Z")))

    def test_conflicting_claim_evidence_remains_contested_instead_of_collapsing(self):
        claim=ContestedClaim(
            "claim:capacity",
            "Facility capacity is 100 units",
            (
                ClaimEvidence(
                    "support","doc-support",dt("2020-01-01T00:00:00Z"),
                    ClaimStance.SUPPORTING,"source-a","Capacity is 100 units",
                ),
                ClaimEvidence(
                    "oppose","doc-oppose",dt("2020-02-01T00:00:00Z"),
                    ClaimStance.OPPOSING,"source-b","Capacity is below 100 units",
                ),
            ),
        )
        self.assertEqual(
            ClaimState.SUPPORT_ONLY,
            claim_state_as_of(claim,dt("2020-01-15T00:00:00Z")),
        )
        self.assertEqual(
            ClaimState.CONTESTED,
            claim_state_as_of(claim,dt("2020-02-01T00:00:00Z")),
        )

    def test_overlapping_capacity_snapshots_survive_without_convenience_collapse(self):
        p1=pp("capacity-source-a")
        p2=pp("capacity-source-b")
        node=Node(
            "processor:disputed","processing","Disputed processor",
            snapshots=(
                Snapshot(date(2020,1,1),known_at=date(2020,1,2),capacity_nameplate=100,capacity_unit="units"),
                Snapshot(date(2020,1,1),known_at=date(2020,1,3),capacity_nameplate=85,capacity_unit="units"),
            ),
            provenance=(p1,p2),
        )
        graph=DependencyGraph([node],[])
        view=graph.as_of(date(2020,2,1),date(2020,2,1))
        self.assertEqual([100,85],[s.capacity_nameplate for s in view.nodes["processor:disputed"].snapshots])

    def test_identical_names_remain_distinct_ids_but_alias_merge_owner_is_absent(self):
        p=pp("identity")
        graph=DependencyGraph(
            [
                Node("facility:alpha-1","processing","Alpha",provenance=(p,)),
                Node("facility:alpha-2","processing","Alpha",provenance=(p,)),
            ],
            [],
        )
        self.assertIsNotNone(graph.resolve_reference("facility:alpha-1",date(2020,1,1),date(2020,1,1)))
        self.assertIsNotNone(graph.resolve_reference("facility:alpha-2",date(2020,1,1),date(2020,1,1)))
        self.assertIsNone(graph.resolve_reference("facility:alpha-legacy",date(2020,1,1),date(2020,1,1)))


if __name__=="__main__":
    unittest.main()
