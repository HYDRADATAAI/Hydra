from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hydra_market_pipeline.hashing import sha256_hex
from hydra_market_pipeline.operations import (
    InjectedInterruption,
    OperationsError,
    _verify_pipeline_artifacts,
    execute_backfill,
    load_backfill_plan,
)
from hydra_market_pipeline.pipeline import load_aliases, run_pipeline as producer_run_pipeline


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "config/backfill_plan.json"
ALIASES = ROOT / "config/symbol_aliases.json"
COPY_IGNORE = shutil.ignore_patterns("build", "__pycache__", "*.pyc")


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
            checkpoint = json.loads(
                (Path(tmp) / "checkpoint.json").read_text(encoding="utf-8")
            )
            _, expected_aliases_sha256 = load_aliases(ALIASES)
            self.assertEqual(
                {
                    entry["aliases_sha256"]
                    for entry in checkpoint["completed"].values()
                },
                {expected_aliases_sha256},
            )

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

    def test_symlinked_persisted_artifacts_fail_closed(self) -> None:
        artifact_names = (
            "manifest.json",
            "resolved_symbol_aliases.json",
            "source_snapshot.csv",
            "normalized_events.csv",
            "normalized_events.jsonl",
            "quarantine_records.jsonl",
        )
        for file_name in artifact_names:
            with self.subTest(file_name=file_name), tempfile.TemporaryDirectory() as tmp:
                output_dir = Path(tmp) / "state"
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )
                checkpoint = json.loads(
                    (output_dir / "checkpoint.json").read_text(encoding="utf-8")
                )
                first = checkpoint["completed"][sorted(checkpoint["completed"])[0]]
                run_dir = output_dir / "runs" / first["pipeline_run_id"]
                artifact_path = run_dir / file_name
                external_copy = Path(tmp) / "outside" / file_name
                external_copy.parent.mkdir()
                external_copy.write_bytes(artifact_path.read_bytes())
                artifact_path.unlink()
                try:
                    artifact_path.symlink_to(external_copy)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlink creation is unavailable: {exc}")

                with self.assertRaisesRegex(OperationsError, "invalid"):
                    execute_backfill(
                        plan_path=PLAN,
                        aliases_path=ALIASES,
                        output_dir=output_dir,
                    )

    def test_symlinked_output_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            external_dir = Path(tmp) / "outside"
            external_dir.mkdir()
            try:
                output_dir.symlink_to(external_dir, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "must not contain symlinks"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )
            self.assertEqual(list(external_dir.iterdir()), [])

    def test_symlinked_new_run_directory_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            runs_root = output_dir / "runs"
            runs_root.mkdir(parents=True)
            plan = load_backfill_plan(plan_path=PLAN, aliases_path=ALIASES)
            result = producer_run_pipeline(
                input_csv=plan.inputs[0].path,
                aliases_path=ALIASES,
            )
            external_run_dir = Path(tmp) / "outside"
            external_run_dir.mkdir()
            run_dir = runs_root / result.pipeline_run_id
            try:
                run_dir.symlink_to(external_run_dir, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "must not be a symlink"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )
            self.assertEqual(list(external_run_dir.iterdir()), [])

    def test_symlinked_new_artifact_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            runs_root = output_dir / "runs"
            runs_root.mkdir(parents=True)
            plan = load_backfill_plan(plan_path=PLAN, aliases_path=ALIASES)
            result = producer_run_pipeline(
                input_csv=plan.inputs[0].path,
                aliases_path=ALIASES,
            )
            run_dir = runs_root / result.pipeline_run_id
            run_dir.mkdir()
            external_file = Path(tmp) / "outside.csv"
            external_file.write_bytes(b"external sentinel")
            try:
                (run_dir / "normalized_events.csv").symlink_to(external_file)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "artifact must not be a symlink"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )
            self.assertEqual(external_file.read_bytes(), b"external sentinel")

    def test_symlinked_output_parent_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            external_dir = Path(tmp) / "outside"
            symlink_parent = Path(tmp) / "linked"
            external_dir.mkdir()
            try:
                symlink_parent.symlink_to(external_dir, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            output_dir = symlink_parent / "state"
            with self.assertRaisesRegex(OperationsError, "must not contain symlinks"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )
            self.assertEqual(list(external_dir.iterdir()), [])

    def test_symlinked_checkpoint_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=output_dir,
            )
            checkpoint_path = output_dir / "checkpoint.json"
            external_checkpoint = Path(tmp) / "outside-checkpoint.json"
            external_checkpoint.write_bytes(checkpoint_path.read_bytes())
            checkpoint_path.unlink()
            try:
                checkpoint_path.symlink_to(external_checkpoint)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "checkpoint must not be a symlink"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )

    def test_symlinked_run_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=output_dir,
            )
            checkpoint = json.loads(
                (output_dir / "checkpoint.json").read_text(encoding="utf-8")
            )
            first = checkpoint["completed"][sorted(checkpoint["completed"])[0]]
            run_dir = output_dir / "runs" / first["pipeline_run_id"]
            external_run_dir = Path(tmp) / "outside" / run_dir.name
            external_run_dir.parent.mkdir()
            run_dir.rename(external_run_dir)
            try:
                run_dir.symlink_to(external_run_dir, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "invalid"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
                )

    def test_symlinked_runs_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "state"
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=output_dir,
            )
            runs_root = output_dir / "runs"
            external_runs_root = Path(tmp) / "outside"
            runs_root.rename(external_runs_root)
            try:
                runs_root.symlink_to(external_runs_root, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(OperationsError, "invalid"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=output_dir,
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

    def test_tampered_checkpoint_alias_digest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            checkpoint_path = Path(tmp) / "checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            first_source_id = sorted(checkpoint["completed"])[0]
            checkpoint["completed"][first_source_id]["aliases_sha256"] = "0" * 64
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(OperationsError, "aliases digest mismatch"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=tmp,
                )

    def test_tampered_manifest_alias_digest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            checkpoint_path = Path(tmp) / "checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            first_source_id = sorted(checkpoint["completed"])[0]
            entry = checkpoint["completed"][first_source_id]
            manifest_path = Path(tmp) / "runs" / entry["pipeline_run_id"] / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["aliases_sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            entry["manifest_sha256"] = sha256_hex(manifest_path.read_bytes())
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(OperationsError, "persisted aliases digest mismatch"):
                execute_backfill(
                    plan_path=PLAN,
                    aliases_path=ALIASES,
                    output_dir=tmp,
                )

    def test_alias_drift_between_partitions_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            sample = sandbox / "sample"
            shutil.copytree(ROOT, sample, ignore=COPY_IGNORE)
            copied_plan = sample / "config/backfill_plan.json"
            copied_aliases = sample / "config/symbol_aliases.json"
            output = sandbox / "state"
            _, pinned_aliases_sha256 = load_aliases(copied_aliases)
            call_count = 0

            def run_with_alias_drift(*, input_csv: Path, aliases_path: Path):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    aliases = json.loads(copied_aliases.read_text(encoding="utf-8"))
                    aliases["AAA"] = "ZZZ"
                    copied_aliases.write_text(
                        json.dumps(aliases, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                return producer_run_pipeline(
                    input_csv=input_csv,
                    aliases_path=aliases_path,
                )

            with patch(
                "hydra_market_pipeline.operations.run_pipeline",
                side_effect=run_with_alias_drift,
            ):
                with self.assertRaisesRegex(OperationsError, "aliases changed while processing"):
                    execute_backfill(
                        plan_path=copied_plan,
                        aliases_path=copied_aliases,
                        output_dir=output,
                    )

            checkpoint = json.loads(
                (output / "checkpoint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(checkpoint["completed"]), 1)
            first_entry = next(iter(checkpoint["completed"].values()))
            self.assertEqual(first_entry["aliases_sha256"], pinned_aliases_sha256)

    def test_persisted_manifest_and_aliases_use_single_byte_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            execute_backfill(
                plan_path=PLAN,
                aliases_path=ALIASES,
                output_dir=tmp,
            )
            checkpoint = json.loads(
                (Path(tmp) / "checkpoint.json").read_text(encoding="utf-8")
            )
            entry = checkpoint["completed"][sorted(checkpoint["completed"])[0]]
            run_dir = Path(tmp) / "runs" / entry["pipeline_run_id"]
            protected = {
                (run_dir / "manifest.json").resolve(),
                (run_dir / "resolved_symbol_aliases.json").resolve(),
            }
            read_counts = {path: 0 for path in protected}
            original_read_bytes = Path.read_bytes
            original_read_text = Path.read_text

            def guarded_read_bytes(path: Path) -> bytes:
                resolved = path.resolve()
                if resolved in read_counts:
                    read_counts[resolved] += 1
                return original_read_bytes(path)

            def guarded_read_text(path: Path, *args, **kwargs) -> str:
                if path.resolve() in protected:
                    raise AssertionError(f"verification reread text from {path.name}")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_bytes", guarded_read_bytes), patch.object(
                Path,
                "read_text",
                guarded_read_text,
            ):
                _verify_pipeline_artifacts(run_dir, entry)

            self.assertEqual(set(read_counts.values()), {1})

    def test_tampered_persisted_input_snapshots_fail_closed(self) -> None:
        for file_name in ("source_snapshot.csv", "resolved_symbol_aliases.json"):
            with self.subTest(file_name=file_name), tempfile.TemporaryDirectory() as tmp:
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
                with (run_dir / file_name).open("ab") as handle:
                    handle.write(b"tampered\n")

                with self.assertRaisesRegex(OperationsError, "input digest mismatch"):
                    execute_backfill(
                        plan_path=PLAN,
                        aliases_path=ALIASES,
                        output_dir=tmp,
                    )

    def test_changed_source_cannot_reuse_old_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            sample = sandbox / "sample"
            shutil.copytree(ROOT, sample, ignore=COPY_IGNORE)
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
            shutil.copytree(ROOT, sample, ignore=COPY_IGNORE)
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
