# HYDRA Market Data Pipeline Sample

Status: **PUBLIC / SYNTHETIC / NON-LIVE**

This directory is a small, runnable data-engineering example that complements
HYDRA's fail-closed validator sample.

It demonstrates a complete synthetic pipeline:

```text
CSV input
  ↓
file-level contract check
  ↓
row validation + normalization
  ↓
deterministic event identity
  ↓
provenance hashes
  ↓
duplicate / defect quarantine
  ↓
JSONL + CSV + deterministic manifest
  ↓
checkpointed backfill + recovery receipt + deterministic SLIs
```

No live market feed, broker connection, trading action, private source data, or
production runtime is represented here.

## What this sample demonstrates

- strict input-column contracts;
- timezone normalization to UTC;
- source-symbol alias normalization;
- decimal price and integer-volume validation;
- deterministic SHA-256 event identity;
- source-file and row-level provenance;
- duplicate-event detection across source aliases;
- row-level quarantine with machine-readable reason codes, validation messages, and stage labels;
- deterministic JSONL, CSV, quarantine, and manifest outputs;
- standard-library runtime implementation with no third-party package dependency;
- unit tests and GitHub Actions CI;
- committed JSON contract files are regression-tested against the runtime CSV requirements and emitted record shapes.
- bounded multi-partition backfills with strict plan contracts and source-byte/partition budgets;
- atomic checkpoints, integrity-checked artifact reuse, and fail-closed plan drift;
- injected interruption recovery whose final artifacts match a clean run byte for byte;
- structured deterministic metrics and explicit partition-completion and row-accounting SLIs.

## Failure semantics

The sample deliberately separates two classes of failure.

**File-level contract drift fails the run.** Missing or unexpected CSV columns
mean the producer contract changed and the file is not processed.

**Row-level data-quality defects quarantine the row.** Invalid timestamps,
prices, volumes, currencies, symbols, or duplicate normalized event identities
are written to the quarantine output while valid rows continue.

## Deterministic identity

The public event identity is:

```text
SHA256(
  canonical_json({
    "symbol": normalized_symbol,
    "event_time_utc": normalized_utc_timestamp,
    "venue": normalized_venue
  })
)
```

That intentionally makes equivalent source aliases collide on one normalized
event identity so the second observation can be quarantined as a duplicate in
this sample.

## Synthetic fixture

`data/raw/synthetic_market_events.csv` contains seven synthetic rows.

Expected result:

- accepted: **3**
- quarantined: **4**
  - one normalized duplicate;
  - one invalid timestamp;
  - one non-positive price;
  - one disallowed synthetic source identifier.

## Run

From this directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m hydra_market_pipeline `
  --input data/raw/synthetic_market_events.csv `
  --aliases config/symbol_aliases.json `
  --output-dir build/demo
```

Expected output files:

```text
build/demo/
  normalized_events.csv
  normalized_events.jsonl
  quarantine_records.jsonl
  manifest.json
```

## Test

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
```

CI runs the same tests, executes the synthetic pipeline, and publishes the
generated sample outputs as a workflow artifact. It also injects a synthetic
interruption after the first backfill partition, resumes from the checkpoint,
and proves that a completed replay performs no new source work.

## Run the recovery proof

From a fresh output directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python run_recovery_demo.py --output-dir build/operations
```

This emits `operations_manifest.json`, `metrics.jsonl`, and
`recovery_receipt.json` plus the content-addressed partition outputs. The SLIs
measure only deterministic behavior in this local synthetic run. They are not
production latency, uptime, reliability, or cost claims.

## Package map

```text
config/
  backfill_plan.json
  symbol_aliases.json
contracts/
  backfill_plan.schema.json
  input_contract.json
  normalized_event.schema.json
  quarantine_record.schema.json
data/raw/
  synthetic_market_events.csv
src/hydra_market_pipeline/
  __init__.py
  __main__.py
  cli.py
  hashing.py
  models.py
  operations.py
  operations_cli.py
  pipeline.py
  writers.py
tests/
  test_contract_files.py
  test_operations.py
  test_pipeline.py
run_recovery_demo.py
```

The purpose is inspectable data-engineering evidence, not a claim of production
market-data operation.
