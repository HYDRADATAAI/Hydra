from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from hydra_market_pipeline import ContractError, run_pipeline, write_outputs


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/synthetic_market_events.csv"
ALIASES = ROOT / "config/symbol_aliases.json"


class MarketDataPipelineTests(unittest.TestCase):
    def test_synthetic_fixture_accepts_three_and_quarantines_four(self) -> None:
        result = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        self.assertEqual(len(result.accepted), 3)
        self.assertEqual(len(result.quarantined), 4)
        self.assertEqual({event.symbol for event in result.accepted}, {"AAA", "BBB", "EEE"})

        errors_by_row = {
            record.source_row_number: set(record.errors)
            for record in result.quarantined
        }
        self.assertEqual(errors_by_row[3], {"duplicate_normalized_event"})
        self.assertEqual(errors_by_row[5], {"event_time_invalid"})
        self.assertEqual(errors_by_row[6], {"price_non_positive"})
        self.assertEqual(errors_by_row[8], {"source_system_invalid"})

        with INPUT.open(newline="", encoding="utf-8") as handle:
            source_rows = list(csv.DictReader(handle))
        self.assertEqual(len(result.accepted) + len(result.quarantined), len(source_rows))
        for record in result.quarantined:
            self.assertEqual(record.stage, "row_validation")
            self.assertEqual(len(record.errors), len(record.validation_messages))
            self.assertTrue(record.raw_record["source_record_id"])

    def test_outputs_are_deterministic_and_csv_matches_jsonl(self) -> None:
        result = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        with tempfile.TemporaryDirectory() as tmp:
            first = write_outputs(result, output_dir=Path(tmp) / "first")
            second = write_outputs(result, output_dir=Path(tmp) / "second")

            self.assertEqual(
                first["normalized_jsonl"].read_bytes(),
                second["normalized_jsonl"].read_bytes(),
            )
            self.assertEqual(
                first["normalized_csv"].read_bytes(),
                second["normalized_csv"].read_bytes(),
            )
            self.assertEqual(
                first["quarantine_jsonl"].read_bytes(),
                second["quarantine_jsonl"].read_bytes(),
            )
            self.assertEqual(
                first["manifest"].read_bytes(),
                second["manifest"].read_bytes(),
            )

            jsonl_events = [
                json.loads(line)
                for line in first["normalized_jsonl"].read_text(encoding="utf-8").splitlines()
            ]
            with first["normalized_csv"].open(newline="", encoding="utf-8") as handle:
                csv_events = list(csv.DictReader(handle))

            self.assertEqual(len(csv_events), 3)
            self.assertEqual(
                [record["event_id"] for record in csv_events],
                [record["event_id"] for record in jsonl_events],
            )
            self.assertEqual(
                [record["event_id"] for record in jsonl_events],
                sorted(record["event_id"] for record in jsonl_events),
            )

            quarantine_records = [
                json.loads(line)
                for line in first["quarantine_jsonl"].read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [record["source_row_number"] for record in quarantine_records],
                sorted(record["source_row_number"] for record in quarantine_records),
            )

            manifest = json.loads(first["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["accepted_rows"], 3)
            self.assertEqual(manifest["quarantined_rows"], 4)
            self.assertEqual(manifest["pipeline_run_id"], result.pipeline_run_id)
            self.assertEqual(
                manifest["outputs"]["normalized_events_csv"]["schema"],
                list(csv_events[0].keys()),
            )

    def test_normalized_identity_and_provenance_are_stable(self) -> None:
        first = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)
        second = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        self.assertEqual(first.pipeline_run_id, second.pipeline_run_id)
        self.assertEqual(
            [event.event_id for event in first.accepted],
            [event.event_id for event in second.accepted],
        )
        self.assertEqual(len({event.event_id for event in first.accepted}), 3)

        for event in first.accepted:
            self.assertEqual(event.source_file_sha256, first.source_file_sha256)
            self.assertEqual(len(event.raw_record_sha256), 64)
            self.assertGreaterEqual(event.source_row_number, 2)
            self.assertEqual(event.transform_version, first.transform_version)

    def test_file_level_contract_drift_fails_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.csv"
            with broken.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "source_system",
                        "source_record_id",
                        "symbol",
                        "event_time",
                        "price",
                        "volume",
                        "currency",
                    ]
                )
                writer.writerow(
                    [
                        "SYNTH_A",
                        "a-001",
                        "AAA",
                        "2026-09-24T17:30:00Z",
                        "10.0",
                        "1",
                        "USD",
                    ]
                )

            with self.assertRaises(ContractError):
                run_pipeline(input_csv=broken, aliases_path=ALIASES)


if __name__ == "__main__":
    unittest.main()
