from __future__ import annotations

import csv
import json
import tempfile
import unittest
from decimal import Decimal, InvalidOperation, ROUND_UP, localcontext
from pathlib import Path

from hydra_market_pipeline import ContractError, run_pipeline, write_outputs
from hydra_market_pipeline.hashing import canonical_json_bytes, sha256_hex
from hydra_market_pipeline.pipeline import _parse_price, load_aliases


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/synthetic_market_events.csv"
ALIASES = ROOT / "config/symbol_aliases.json"


class MarketDataPipelineTests(unittest.TestCase):
    def test_synthetic_fixture_accepts_three_and_quarantines_four(self) -> None:
        result = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        self.assertEqual(len(result.accepted), 3)
        self.assertEqual(len(result.quarantined), 4)
        self.assertEqual({event.symbol for event in result.accepted}, {"AAA", "BBB", "EEE"})
        self.assertEqual(result.source_csv_bytes, INPUT.read_bytes())
        self.assertEqual(
            dict(result.resolved_aliases),
            json.loads(ALIASES.read_text(encoding="utf-8")),
        )

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
            self.assertEqual(
                first["source_snapshot"].read_bytes(),
                second["source_snapshot"].read_bytes(),
            )
            self.assertEqual(
                first["resolved_aliases_json"].read_bytes(),
                second["resolved_aliases_json"].read_bytes(),
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
            self.assertEqual(manifest["schema_version"], "hydra-market-pipeline-manifest/v2")
            self.assertEqual(manifest["source_rows"], 7)
            self.assertEqual(
                set(manifest["inputs"]),
                {"resolved_aliases_json", "source_csv"},
            )
            self.assertEqual(first["source_snapshot"].read_bytes(), INPUT.read_bytes())
            self.assertEqual(
                sha256_hex(first["source_snapshot"].read_bytes()),
                manifest["source_file_sha256"],
            )
            self.assertEqual(
                first["resolved_aliases_json"].read_bytes(),
                canonical_json_bytes(dict(result.resolved_aliases)),
            )
            self.assertEqual(
                sha256_hex(first["resolved_aliases_json"].read_bytes()),
                manifest["aliases_sha256"],
            )
            self.assertEqual(
                manifest["outputs"]["normalized_events_jsonl"]["sha256"],
                "ec902bc92942197ddceb737b90421f36298b660c0788c99ac4c18b2e1c570e86",
            )
            self.assertEqual(
                manifest["outputs"]["normalized_events_csv"]["sha256"],
                "c6528dfef24217c710a0eabaafd67c30da9b2a4d544be36a27bc1ca6a5c17385",
            )
            self.assertEqual(
                manifest["outputs"]["quarantine_records_jsonl"]["sha256"],
                "4fd967d69e63ae92d5862ef8a69803b3071ac3c20d54f7d5738bd4f7a5a6a861",
            )
            self.assertEqual(
                manifest["outputs"]["normalized_events_csv"]["schema"],
                list(csv_events[0].keys()),
            )

    def test_trimmed_headers_are_used_for_row_lookup(self) -> None:
        source = INPUT.read_bytes()
        header, body = source.split(b"\n", 1)
        padded = b",".join(b" " + field + b" " for field in header.split(b","))
        expected = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        with tempfile.TemporaryDirectory() as tmp:
            padded_input = Path(tmp) / "padded.csv"
            padded_input.write_bytes(padded + b"\n" + body)
            actual = run_pipeline(input_csv=padded_input, aliases_path=ALIASES)

        self.assertEqual(
            [event.symbol for event in actual.accepted],
            [event.symbol for event in expected.accepted],
        )
        self.assertEqual(
            [record.errors for record in actual.quarantined],
            [record.errors for record in expected.quarantined],
        )
        self.assertEqual(
            [dict(record.raw_record) for record in actual.quarantined],
            [dict(record.raw_record) for record in expected.quarantined],
        )

    def test_normalized_identity_and_provenance_are_stable(self) -> None:
        first = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)
        second = run_pipeline(input_csv=INPUT, aliases_path=ALIASES)

        self.assertEqual(first.pipeline_run_id, second.pipeline_run_id)
        self.assertEqual(
            first.pipeline_run_id,
            "9f03988bf0bc7245e85d13211ed0af8715da2c4e7464f2f7639a8532c33f3c0d",
        )
        self.assertEqual(
            [event.event_id for event in first.accepted],
            [event.event_id for event in second.accepted],
        )
        self.assertEqual(len({event.event_id for event in first.accepted}), 3)
        self.assertEqual(
            [event.event_id for event in first.accepted],
            [
                "0dc3a510144754af42f61cf3a72f51fcbf90aed765d28053032e8fb857946458",
                "5661c842227f80f2866a673d1e09c092fb7de3a2c3663eaa3f018953d0aa516c",
                "5dce66c1857f0ebbdfad7a907e8ee839592f303dd768cb238aff06112f3bd271",
            ],
        )

        for event in first.accepted:
            self.assertEqual(event.source_file_sha256, first.source_file_sha256)
            self.assertEqual(len(event.raw_record_sha256), 64)
            self.assertGreaterEqual(event.source_row_number, 2)
            self.assertEqual(event.transform_version, first.transform_version)

    def test_unterminated_quoted_row_rejects_the_entire_file(self) -> None:
        malformed = (
            b"source_system,source_record_id,symbol,event_time,price,volume,currency,venue\n"
            b'SYNTH_A,bad-001,AAA,"unterminated\n'
            b"SYNTH_A,good-002,BBB,2026-09-24T17:30:00Z,1.25,1,USD,XNAS\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "malformed.csv"
            source.write_bytes(malformed)
            with self.assertRaisesRegex(ContractError, "input CSV is malformed"):
                run_pipeline(input_csv=source, aliases_path=ALIASES)

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

    def test_alias_config_rejects_duplicate_and_normalized_colliding_keys(self) -> None:
        cases = (
            ('{"AAA":"AAA","AAA":"BBB"}', "duplicate key"),
            ('{"AAA":"AAA"," aaa ":"BBB"}', "normalized-key collision"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            aliases_path = Path(tmp) / "aliases.json"
            for payload, expected_error in cases:
                with self.subTest(expected_error=expected_error):
                    aliases_path.write_text(payload, encoding="utf-8")
                    with self.assertRaisesRegex(ContractError, expected_error):
                        load_aliases(aliases_path)

    def test_price_quantization_ignores_ambient_decimal_context(self) -> None:
        with localcontext() as ambient:
            ambient.prec = 2
            ambient.rounding = ROUND_UP
            ambient.traps[InvalidOperation] = False
            errors: list[str] = []
            price = _parse_price("123456789.123456", errors)

        self.assertEqual(price, Decimal("123456789.123456"))
        self.assertEqual(errors, [])

    def test_price_quantization_has_deterministic_precision_boundary(self) -> None:
        valid_errors: list[str] = []
        valid_text = "9" * 22 + ".123456"
        self.assertEqual(_parse_price(valid_text, valid_errors), Decimal(valid_text))
        self.assertEqual(valid_errors, [])

        invalid_errors: list[str] = []
        invalid_text = "9" * 23 + ".123456"
        self.assertIsNone(_parse_price(invalid_text, invalid_errors))
        self.assertEqual(invalid_errors, ["price_invalid"])


if __name__ == "__main__":
    unittest.main()
