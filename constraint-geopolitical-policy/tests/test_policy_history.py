import unittest
from datetime import datetime, timezone

from hydra_constraint_policy.model import (
    ClaimKind, EventType, HistoricalEvent, Provenance, Relation, TemporalFacts,
    ValidationError, eligible_as_of, warning_signs_as_of,
)

UTC = timezone.utc
def dt(s): return datetime.fromisoformat(s).replace(tzinfo=UTC)

def prov(doc="doc-1", available="2022-01-01T12:00:00", version="1"):
    return Provenance("official-source", doc, dt(available), dt(available), version, "sha256:abc")

def event(**kw):
    base = dict(
        event_id="evt-1", event_type=EventType.EXPORT_CONTROL, title="Control announced",
        temporal=TemporalFacts(dt("2022-01-01T12:00:00"), dt("2022-02-01T00:00:00")),
        provenance=(prov(),),
        relations=(Relation("CONSTRAINT", "constraint:semiconductor-capacity", .9, ("doc-1",)),),
    )
    base.update(kw)
    return HistoricalEvent(**base)

class PolicyHistoryTests(unittest.TestCase):
    def test_valid(self):
        event().validate()

    def test_future_information_rejected_from_replay(self):
        self.assertEqual([], eligible_as_of([event()], dt("2021-12-31T23:59:59")))

    def test_known_effective_are_distinct(self):
        e=event()
        self.assertLess(e.temporal.known_at, e.temporal.effective_at)

    def test_partial_future_provenance_not_leaked(self):
        e=event(provenance=(prov(), prov("doc-2","2023-01-01T00:00:00")))
        self.assertEqual([], eligible_as_of([e], dt("2022-06-01T00:00:00")))

    def test_missing_provenance_fails(self):
        with self.assertRaises(ValidationError):
            event(provenance=()).validate()

    def test_bad_relation_reference_fails(self):
        with self.assertRaises(ValidationError):
            event(relations=(Relation("CONSTRAINT","x",.8,("missing",)),)).validate()

    def test_unsupported_causality_fails(self):
        with self.assertRaises(ValidationError):
            event(causal=True).validate()

    def test_unsupported_motive_fails(self):
        with self.assertRaises(ValidationError):
            event(motive_claim=True).validate()

    def test_attributed_explanation_allowed(self):
        event(motive_claim=True, claim_kind=ClaimKind.ATTRIBUTED_EXPLANATION, attributed_to="source").validate()

    def test_resolution_before_effective_fails(self):
        with self.assertRaises(ValidationError):
            event(temporal=TemporalFacts(dt("2022-01-01T12:00:00"),dt("2022-02-01T00:00:00"),resolved_at=dt("2022-01-15T00:00:00"))).validate()

    def test_warning_sign_as_of(self):
        got=warning_signs_as_of([event()],"constraint:semiconductor-capacity",dt("2022-01-02T00:00:00"))
        self.assertEqual(["evt-1"],[x.event_id for x in got])

    def test_deterministic_digest(self):
        self.assertEqual(event().canonical_digest(), event().canonical_digest())

if __name__ == "__main__":
    unittest.main()
