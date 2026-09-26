# HYDRA T6 Fail-Closed Validator

Status: **SOURCE-ONLY, DORMANT, NOT ACTIVATED**

This directory contains a focused public implementation example for HYDRA's
fail-closed candidate-handoff boundary. The component validates authority,
candidate-only handoff semantics, deterministic receipts, native T5→T6
implementation-admission receipts, and dormant integration behavior without
enabling canonical promotion or external effects.

Its authority-smuggling scanner recognizes camelCase, PascalCase,
mixed-acronym, separator-delimited, punctuation-delimited, compacted, Unicode
compatibility, common mixed-script confusable forms, and embedded strong-marker wrappers.

## What this sample demonstrates

- strict JSON parsing with deterministic canonical encoding and bounded structural depth;
- authority-envelope validation with explicit digest/scope bindings;
- candidate-only handoff validation;
- an artifact-pinned native T5→T6 implementation-admission gate with explicit
  identity, binding, freshness, revocation, supersession, and signature checks;
- admission receipts that cannot grant runtime activation, canonical promotion,
  live sources, model training, or trading;
- rejection of compacted, mixed-case, and Unicode authority smuggling;
- deterministic `ABSTAIN` / `QUARANTINE` receipts;
- an integration adapter that remains explicitly dormant;
- focused unit tests and GitHub Actions CI.

## Package map

```text
src/hydra_t6_failclosed/
  authority.py                  validator authority envelope + signature validation
  documents.py                  strict JSON parsing + deterministic hashing
  handoff.py                    candidate-handoff contract validation
  native_binding_admission.py   exact-artifact T5→T6 implementation admission gate
  receipt.py                    inert deterministic receipt construction
  service.py                    pure fail-closed orchestration
  dormant_adapter.py            integration boundary that refuses activation
tests/
  test_adversarial_parser_fuzz.py
  test_authority.py
  test_camelcase_smuggling.py
  test_documents.py
  test_dormant_adapter.py
  test_native_binding_admission.py
  test_receipt.py
  test_thread6_successor_reconciliation.py
```

## Admission boundary

Implementation admission is separate from semantic closure.

The native-binding gate requires all of the following before it can return
`ADMITTED_EXACT_ARTIFACT`:

- an exact implementation manifest;
- artifact and test-evidence SHA-256 bindings;
- the frozen T5 producer and T6 consumer namespaces;
- the admitted handoff/candidate schemas;
- explicit semantic authority pins;
- a current, non-revoked signed admission receipt from the
  `IMPLEMENTATION_CONTRACT` authority role.

Missing authority fails closed. A valid implementation-admission receipt still
does **not** authorize runtime activation, canonical promotion, live-source
acquisition, model training, or trading.

## Safety boundary

The validator returns only `ABSTAIN` or `QUARANTINE` for candidate
validation. The implementation-admission gate only evaluates whether an exact
artifact has a valid admission receipt.

This package does **not**:

- rank candidates;
- select canonical truth;
- mutate a canonical store;
- self-register into a runtime;
- authorize live sources;
- authorize model training or trading;
- perform external effects.

Bound policies, schemas, oracle data, real admission authority records, sealed
review artifacts, reports, and external conformance fixtures are intentionally
excluded from this public source sample.

## Run the tests

From this directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
```

The same command runs in GitHub Actions on Python 3.11.

[View validator CI →](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml)
