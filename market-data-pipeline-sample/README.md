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
JSONL + Parquet + deterministic manifest
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
- row-level quarantine with machine-readable reason codes;
- deterministic JSONL outputs and run manifest;
- typed Parquet output through PyArrow;
- unit tests and GitHub Actions CI;
- committed JSON contract files are regression-tested against the runtime CSV requirements and emitted record shapes.

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

`data/raw/synthetic_market_events.csv` contains six synthetic rows.

Expected result:

- accepted: **3**
- quarantined: **3**
  - one normalized duplicate;
  - one invalid timestamp;
  - one non-positive price.

## Run

From this directory:

```powershell
python -m pip install -e .
python -m hydra_market_pipeline `
  --input data/raw/synthetic_market_events.csv `
  --aliases config/symbol_aliases.json `
  --output-dir build/demo
```

Expected output files:

```text
build/demo/
  normalized_events.jsonl
  normalized_events.parquet
  quarantine_records.jsonl
  manifest.json
```

## Test

```powershell
python -m unittest discover -s tests -t . -v
```

CI runs the same tests, executes the synthetic pipeline, and publishes the
generated sample outputs as a workflow artifact.

## Package map

```text
config/
  symbol_aliases.json
contracts/
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
  pipeline.py
  writers.py
tests/
  test_contract_files.py
  test_pipeline.py
```

The purpose is inspectable data-engineering evidence, not a claim of production
market-data operation.
