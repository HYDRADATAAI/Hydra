from __future__ import annotations

import copy
import unittest

from validate_constraint_semiconductor_pass004_source_seed import load_inputs, validate


class SemiconductorSeedTests(unittest.TestCase):
    def test_reviewed_seed(self):
        self.assertEqual(validate(*load_inputs())["reviewed_evidence_observations"], 8)

    def test_negative_boundaries(self):
        def set_field(d, field, value):
            d[2]["field_updates"][0][field] = value

        mutations = {
            "backdated_source": lambda d: d[0]["sources"][0].update(available_at="2024-04-03T00:00:00Z"),
            "fake_raw_capture": lambda d: d[0].update(source_content_persisted=True),
            "duplicate_source": lambda d: d[0]["sources"].append(copy.deepcopy(d[0]["sources"][0])),
            "orphan_observation": lambda d: d[1]["observations"][0].update(source_id="SRC-MISSING"),
            "orphan_field": lambda d: set_field(d, "evidence_ids", ["EV-MISSING"]),
            "backdated_observation": lambda d: d[1]["observations"][0].update(available_at="2024-04-03T00:00:00Z"),
            "backdated_field": lambda d: set_field(d, "available_at", "2024-04-03T00:00:00Z"),
            "invented_source_version": lambda d: d[0]["sources"][0].update(source_version_id="SV-UNPROVEN"),
            "unknown_capacity_to_zero": lambda d: (set_field(d, "field_name", "effective_capacity"), set_field(d, "value", 0)),
            "invented_runtime_admission": lambda d: d[2].update(runtime_admitted=True),
            "field_namespace_fork": lambda d: set_field(d, "field_name", "semiconductor_master_score"),
            "fake_replay_coverage": lambda d: d[2].update(required_cases_executed=14),
            "fabricated_effective_date": lambda d: d[1]["observations"][0].update(effective_from="2024-04-03"),
            "missing_unknown_boundary": lambda d: d[2]["unresolved_fields"].remove("facility_id"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                docs = copy.deepcopy(load_inputs())
                mutate(docs)
                with self.assertRaises(ValueError):
                    validate(*docs)


if __name__ == "__main__":
    unittest.main()
