import unittest
from datetime import datetime, timezone

from hydra_constraint_replay.models import Evidence
from hydra_constraint_policy.model import EventType, HistoricalEvent, Provenance, Relation, TemporalFacts
from hydra_constraint_policy.replay_adapter import to_replay_evidence

UTC=timezone.utc
def dt(s): return datetime.fromisoformat(s).replace(tzinfo=UTC)

class ReplayAdapterTests(unittest.TestCase):
    def sample(self, metadata=None):
        p=Provenance("official","doc-1",dt("2022-01-01T12:00:00"),dt("2022-01-01T12:00:00"),"1","sha256:abc")
        return HistoricalEvent(
            "evt-1",EventType.EXPORT_CONTROL,"Control announced",
            TemporalFacts(dt("2022-01-01T12:00:00"),dt("2022-02-01T00:00:00"),dt("2022-03-01T00:00:00")),
            (p,),(Relation("CONSTRAINT","constraint:x",.9,("doc-1",)),),
            metadata=metadata or {"source_uris":{"doc-1":"https://example.invalid/official"}}
        )

    def test_maps_to_authoritative_replay_model(self):
        r=to_replay_evidence(self.sample())[0]
        self.assertIsInstance(r,Evidence)
        self.assertEqual("evt-1:doc-1:1",r.evidence_id)
        self.assertEqual("sha256:abc",r.source_hash)
        self.assertEqual("constraint:x",r.payload["relations"][0]["entity_id"])

    def test_missing_source_uri_fails_closed(self):
        with self.assertRaises(ValueError):
            to_replay_evidence(self.sample({"source_uris":{}}))

if __name__=="__main__":
    unittest.main()
