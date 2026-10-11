from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from function.processor import (
    MAX_SOURCE_ROWS,
    ContractError,
    TRANSFORM_VERSION,
    process_csv,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "synthetic_market_events.csv"


class ProcessorTests(unittest.TestCase):
    def test_row_limit_is_enforced_before_batch_outputs_are_built(self):
        self.assertEqual(MAX_SOURCE_ROWS, 10_000)
        header = (
            b"source_system,source_record_id,symbol,event_time,price,volume,currency,venue\n"
        )
        row = b"SYNTH_A,a-001,AAA,2026-09-24T17:30:00Z,1.25,1,USD,XNAS\n"

        with patch("function.processor.MAX_SOURCE_ROWS", 1):
            one_row = process_csv(header + row)
            self.assertEqual(len(one_row.accepted), 1)
            with self.assertRaisesRegex(ContractError, "max_rows=1"):
                process_csv(header + row + row)

    def test_expected_outcomes_and_no_silent_loss(self):
        batch = process_csv(FIXTURE.read_bytes())

        self.assertEqual(len(batch.accepted), 3)
        self.assertEqual(len(batch.quarantined), 4)
        self.assertEqual(len(batch.accepted) + len(batch.quarantined), 7)
        self.assertEqual(
            [record["source_row_number"] for record in batch.quarantined],
            [3, 5, 6, 8],
        )
        reasons = {
            error
            for record in batch.quarantined
            for error in record["errors"]
        }
        self.assertEqual(
            reasons,
            {
                "duplicate_normalized_event",
                "event_time_invalid",
                "price_non_positive",
                "source_system_invalid",
            },
        )

    def test_normalization_identity_and_lineage(self):
        batch = process_csv(FIXTURE.read_bytes())
        accepted_by_symbol = {record["symbol"]: record for record in batch.accepted}
        aaa = accepted_by_symbol["AAA"]

        self.assertEqual(aaa["event_time_utc"], "2026-09-24T17:30:00.000000Z")
        self.assertEqual(aaa["price"], "101.250000")
        self.assertEqual(aaa["currency"], "USD")
        self.assertEqual(aaa["pipeline_run_id"], batch.run_id)
        self.assertEqual(aaa["source_file_sha256"], batch.source_file_sha256)
        self.assertEqual(aaa["transform_version"], TRANSFORM_VERSION)
        self.assertEqual(len(aaa["event_id"]), 64)
        self.assertEqual(len(aaa["raw_record_sha256"]), 64)

    def test_outputs_are_byte_stable(self):
        first = process_csv(FIXTURE.read_bytes())
        second = process_csv(FIXTURE.read_bytes())

        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(first.artifacts, second.artifacts)
        manifest = json.loads(first.artifacts["manifest.json"])
        self.assertEqual(manifest["accepted_rows"], 3)
        self.assertEqual(manifest["quarantined_rows"], 4)
        self.assertEqual(manifest["pipeline_run_id"], first.run_id)

    def test_malformed_quoted_row_rejects_the_entire_file(self):
        malformed = (
            b"source_system,source_record_id,symbol,event_time,price,volume,currency,venue\n"
            b'SYNTH_A,bad-001,AAA,"unterminated\n'
            b"SYNTH_A,good-002,BBB,2026-09-24T17:30:00Z,1.25,1,USD,XNAS\n"
        )
        with self.assertRaisesRegex(ContractError, "input CSV is malformed"):
            process_csv(malformed)

    def test_file_contract_fails_closed(self):
        malformed = b"symbol,price\nAAA,1.0\n"
        with self.assertRaisesRegex(ContractError, "contract mismatch"):
            process_csv(malformed)

    def test_local_artifacts_can_be_written_without_dependencies(self):
        batch = process_csv(FIXTURE.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name, content in batch.artifacts.items():
                (target / name).write_bytes(content)
            self.assertEqual(
                sorted(path.name for path in target.iterdir()),
                [
                    "manifest.json",
                    "normalized_events.jsonl",
                    "quarantine_records.jsonl",
                ],
            )


if __name__ == "__main__":
    unittest.main()
