from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hydra_market_pipeline.hashing import sha256_hex
from hydra_market_pipeline.operations import (
    InjectedInterruption,
    OperationsError,
    execute_backfill,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "config/backfill_plan.json"
ALIASES = ROOT / "config/symbol_aliases.json"


class OperationsTests(unittest.TestCase):
    def test_backfill_emits_complete_metrics_and_visible_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outcome = execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            manifest = json.loads(outcome.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["status"], "PASS")
            self.assertEqual(manifest["data_boundary"], "synthetic_non_live")
            self.assertEqual(manifest["metrics"]["planned_partitions"], 2)
            self.assertEqual(manifest["metrics"]["completed_partitions"], 2)
            self.assertEqual(manifest["metrics"]["accepted_rows"], 6)
            self.assertEqual(manifest["metrics"]["quarantined_rows"], 5)
            self.assertEqual(manifest["metrics"]["source_rows"], 11)
            self.assertEqual(
                manifest["slis"]["partition_completion_ratio"]["value"],
                "1.000000",
            )
            self.assertEqual(
                manifest["slis"]["row_accounting_ratio"]["value"],
                "1.000000",
            )
            self.assertEqual(len(outcome.metrics_path.read_text().splitlines()), 8)
            first_metric = json.loads(
                outcome.metrics_path.read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertEqual(first_metric["backfill_id"], outcome.backfill_id)
            self.assertEqual(first_metric["data_boundary"], "synthetic_non_live")

    def test_interrupted_resume_matches_clean_run_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            interrupted_dir = Path(tmp) / "interrupted"
            clean_dir = Path(tmp) / "clean"
            with self.assertRaises(InjectedInterruption):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=interrupted_dir,
                    interrupt_after_new_sources=1,
                )

            resumed = execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=interrupted_dir,
            )
            clean = execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=clean_dir,
            )

            self.assertEqual(len(resumed.reused_sources), 1)
            self.assertEqual(len(resumed.processed_sources), 1)
            self.assertEqual(
                resumed.manifest_path.read_bytes(),
                clean.manifest_path.read_bytes(),
            )
            self.assertEqual(
                resumed.metrics_path.read_bytes(),
                clean.metrics_path.read_bytes(),
            )

    def test_completed_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            manifest_sha = sha256_hex(first.manifest_path.read_bytes())
            second = execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )

            self.assertEqual(second.processed_sources, ())
            self.assertEqual(len(second.reused_sources), 2)
            self.assertEqual(sha256_hex(second.manifest_path.read_bytes()), manifest_sha)

    def test_tampered_persisted_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            checkpoint = json.loads(
                (Path(tmp) / "checkpoint.json").read_text(encoding="utf-8")
            )
            first = checkpoint["completed"][sorted(checkpoint["completed"])[0]]
            run_dir = Path(tmp) / "runs" / first["pipeline_run_id"]
            with (run_dir / "normalized_events.jsonl").open("ab") as handle:
                handle.write(b"tampered\n")

            with self.assertRaisesRegex(OperationsError, "digest mismatch"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=tmp,
                )

    def test_tampered_checkpoint_row_accounting_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            checkpoint_path = Path(tmp) / "checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            first_source_id = sorted(checkpoint["completed"])[0]
            checkpoint["completed"][first_source_id]["source_rows"] += 1
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(OperationsError, "row accounting mismatch"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=tmp,
                )

    def test_changed_source_cannot_reuse_old_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            sample = sandbox / "sample"
            shutil.copytree(ROOT, sample)
            copied_plan = sample / "config/backfill_plan.json"
            copied_aliases = sample / "config/symbol_aliases.json"
            output = sandbox / "state"
            execute_backfill(
                plan_path=copied_plan,
                aliases_path=copied_aliases,
                output_dir=output,
            )
            with (sample / "data/raw/synthetic_market_events_day2.csv").open(
                "ab"
            ) as handle:
                handle.write(b"\n")

            with self.assertRaisesRegex(OperationsError, "current pinned plan"):
                execute_backfill(
                    plan_path=copied_plan,
                    aliases_path=copied_aliases,
                    output_dir=output,
                )

    def test_source_byte_budget_fails_before_checkpoint_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            sample = sandbox / "sample"
            shutil.copytree(ROOT, sample)
            plan_path = sample / "config/backfill_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["max_total_source_bytes"] = 1
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            output = sandbox / "state"

            with self.assertRaisesRegex(OperationsError, "source-byte budget"):
                execute_backfill(
                    plan_path=plan_path,
                    aliases_path=sample / "config/symbol_aliases.json",
                    output_dir=output,
                )
            self.assertFalse((output / "checkpoint.json").exists())


if __name__ == "__main__":
    unittest.main()
