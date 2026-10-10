from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_market_pipeline.pipeline import REQUIRED_COLUMNS, run_pipeline
from hydra_market_pipeline.writers import write_outputs


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/synthetic_market_events.csv"
ALIASES = ROOT / "config/symbol_aliases.json"
CONTRACTS = ROOT / "contracts"


class ContractFileSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

    def test_input_contract_matches_runtime_required_columns(self) -> None:
        contract = json.loads(
            (CONTRACTS / "input_contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            tuple(contract["required_columns"]),
            REQUIRED_COLUMNS,
        )
        self.assertFalse(contract["additional_columns_allowed"])

    def test_normalized_event_schema_matches_emitted_record_shape(self) -> None:
        schema = json.loads(
            (CONTRACTS / "normalized_event.schema.json").read_text(encoding="utf-8")
        )
        record = self.result.accepted[0].json_record()

        self.assertEqual(set(schema["required"]), set(record))
        self.assertEqual(set(schema["properties"]), set(record))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["transform_version"]["const"],
            record["transform_version"],
        )

    def test_quarantine_schema_matches_emitted_record_shape(self) -> None:
        schema = json.loads(
            (CONTRACTS / "quarantine_record.schema.json").read_text(encoding="utf-8")
        )
        record = self.result.quarantined[0].json_record()

        self.assertEqual(set(schema["required"]), set(record))
        self.assertEqual(set(schema["properties"]), set(record))
        self.assertFalse(schema["additionalProperties"])
        self.assertTrue(record["errors"])

    def test_backfill_plan_schema_matches_committed_plan(self) -> None:
        schema = json.loads(
            (CONTRACTS / "backfill_plan.schema.json").read_text(encoding="utf-8")
        )
        plan = json.loads(
            (ROOT / "config/backfill_plan.json").read_text(encoding="utf-8")
        )

        self.assertEqual(set(schema["required"]), set(plan))
        self.assertEqual(set(schema["properties"]), set(plan))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            plan["schema_version"],
        )
        self.assertLessEqual(len(plan["inputs"]), plan["max_partitions"])

    def test_pipeline_manifest_schema_matches_emitted_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outputs = write_outputs(self.result, output_dir=tmp)
            manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))
        schema = json.loads(
            (CONTRACTS / "pipeline_manifest.schema.json").read_text(encoding="utf-8")
        )

        self.assertEqual(set(schema["required"]), set(manifest))
        self.assertEqual(set(schema["properties"]), set(manifest))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            manifest["schema_version"],
        )
        for group in ("inputs", "outputs"):
            group_schema = schema["properties"][group]
            self.assertEqual(set(group_schema["required"]), set(manifest[group]))
            self.assertEqual(set(group_schema["properties"]), set(manifest[group]))
            self.assertFalse(group_schema["additionalProperties"])
            for name, descriptor in manifest[group].items():
                descriptor_schema = group_schema["properties"][name]
                self.assertEqual(
                    set(descriptor_schema["required"]),
                    set(descriptor),
                )
                self.assertFalse(descriptor_schema["additionalProperties"])
                self.assertEqual(
                    descriptor_schema["properties"]["file"]["const"],
                    descriptor["file"],
                )


if __name__ == "__main__":
    unittest.main()
