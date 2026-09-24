# HYDRA T6 Fail-Closed Validator

Status: **SOURCE-ONLY, DORMANT, NOT ACTIVATED**

This directory contains a focused public implementation example for HYDRA's
fail-closed candidate-handoff boundary. The component validates authority,
candidate-only handoff semantics, deterministic receipts, and dormant
integration behavior without enabling canonical promotion or external effects.

## What this sample demonstrates

- strict JSON parsing with deterministic canonical encoding;
- authority-envelope validation with explicit digest/scope bindings;
- candidate-only handoff validation;
- rejection of authority smuggling, including camelCase and PascalCase forms;
- deterministic `ABSTAIN` / `QUARANTINE` receipts;
- an integration adapter that remains explicitly dormant;
- focused unit tests and GitHub Actions CI.

## Package map

```text
src/hydra_t6_failclosed/
  authority.py         authority envelope + signature validation
  documents.py         strict JSON parsing + deterministic hashing
  handoff.py           candidate-handoff contract validation
  receipt.py           inert deterministic receipt construction
  service.py           pure fail-closed orchestration
  dormant_adapter.py   integration boundary that refuses activation
tests/
  test_camelcase_smuggling.py
  test_dormant_adapter.py
```

## Safety boundary

The validator returns only `ABSTAIN` or `QUARANTINE`.

It does **not**:

- rank candidates;
- select canonical truth;
- mutate a canonical store;
- self-register into a runtime;
- authorize model training or trading;
- perform external effects.

Bound policies, schemas, oracle data, authority records, sealed review
artifacts, reports, and external conformance fixtures are intentionally
excluded from this public source sample.

## Run the tests

From this directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
```

The same command runs in GitHub Actions on Python 3.11.

[View validator CI →](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml)
