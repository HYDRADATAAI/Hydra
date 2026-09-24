from __future__ import annotations

import json
import unittest
from pathlib import Path

from hydra_market_pipeline.pipeline import REQUIRED_COLUMNS, run_pipeline


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


if __name__ == "__main__":
    unittest.main()
