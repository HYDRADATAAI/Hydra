# HYDRA

**Market Intelligence & Data Engineering System**

> Turn fragmented market data into traceable intelligence.

[![T6 fail-closed validator](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml)
[![Market data pipeline sample](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml)

**Project site:** https://hydradataai.github.io/Hydra-Website/  
**Technical site repository:** https://github.com/HYDRADATAAI/Hydra-Website

## What HYDRA is

HYDRA is a data-engineering system built to turn fragmented market and reference data into governed, traceable analytical evidence.

The engineering focus is not “generate a signal and hope.” It is the machinery underneath reliable analytical systems:

- multi-source ingestion and normalization;
- deterministic identity and canonicalization;
- schema and contract validation;
- field-level source authority;
- provenance and lineage;
- cross-stage handoff validation;
- reproducible data transformations;
- quarantine and release gates;
- fail-closed behavior when required evidence or authority is missing.

The project uses market intelligence as the domain, but the core problems are general data-engineering problems: heterogeneous sources, inconsistent schemas, identity mapping, lineage, reproducibility, contract drift, and trustworthy downstream consumption.

## The problem I built it to solve

Market data rarely arrives as one clean, authoritative table.

Different sources may disagree on identity, timestamps, field semantics, coverage, or ownership. A downstream component can appear to “work” while quietly receiving information that no upstream producer actually had authority to provide.

HYDRA treats that as an engineering defect.

A downstream field must be:

1. observed from an authoritative source;
2. produced by the component that owns it; or
3. derived under an explicit, reproducible contract.

If none of those are true, the pipeline blocks rather than fabricating a green result.

## What I built

### Data ingestion and normalization

Pipelines for bringing heterogeneous market, historical, reference, profile, options/context, and research artifacts into controlled downstream structures.

### Contract-bound handoffs

Validation at pipeline seams so a downstream stage cannot silently accept fields that were never legitimately produced upstream.

### Provenance and lineage

Artifacts carry enough source and transformation context to answer:

- Where did this value come from?
- Which component owned it?
- Was it observed or derived?
- Can the transformation be reproduced?
- What should happen if the required authority is absent?

### Deterministic validation

Regression, replay, integrity, immutability, and handoff tests are used to keep repairs bounded and reproducible.

### Failure semantics

HYDRA distinguishes between:

- `PASS`
- `FAIL_WITH_DEFECT`
- `BLOCKED_BY_MISSING_AUTHORITY`

A truthful blocker is preferable to an output that looks complete but cannot be justified.

## System shape

```text
fragmented sources
        ↓
ingestion / normalization
        ↓
identity + schema contracts
        ↓
source-authority / provenance gates
        ↓
context + constraint processing
        ↓
validation / quarantine / release gates
        ↓
traceable research and analytical outputs
```

Machine learning is treated as a downstream consumer of governed data, not as a substitute for data quality, lineage, or source authority.

## Recent engineering proof

A bounded constraint-integration run exercised the current authority-scope controls against pinned native source archives.

The run:

- passed 42 containment regressions;
- passed 5 streaming/native-source tests;
- examined 1,212 upstream candidate objects;
- verified the native contract pin;
- performed no HYDRA writes;
- executed no native handoff when producer authority could not be proven;
- terminated truthfully as `BLOCKED_BY_MISSING_AUTHORITY`.

That behavior is intentional: missing provenance is not converted into invented data merely to make a pipeline appear green.

## Public data-engineering pipeline sample

A second runnable public example lives in [`market-data-pipeline-sample/`](market-data-pipeline-sample/). It uses **synthetic, non-live** records to demonstrate a compact end-to-end data pipeline:

`CSV → contract check → normalization → deterministic identity → provenance → quarantine → JSONL / Parquet → manifest`

The sample intentionally distinguishes **file-level contract drift** from **row-level data-quality defects**: incompatible file schemas fail the run, while malformed or duplicate rows are quarantined with machine-readable reason codes.

Key evidence:

- [`pipeline.py`](market-data-pipeline-sample/src/hydra_market_pipeline/pipeline.py) performs strict contract checks, normalization, deterministic event identity, provenance hashing, and quarantine decisions.
- [`writers.py`](market-data-pipeline-sample/src/hydra_market_pipeline/writers.py) emits deterministic JSONL, typed Parquet, and a deterministic run manifest.
- [`test_pipeline.py`](market-data-pipeline-sample/tests/test_pipeline.py) verifies expected accept/quarantine counts, deterministic reruns, Parquet equivalence, provenance, and file-level contract failure.
- [Market data pipeline CI](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml) runs the tests, executes the synthetic fixture, verifies the manifest, and publishes the generated outputs as a workflow artifact.

From the sample directory:

```powershell
python -m pip install -e .
python -m unittest discover -s tests -t . -v
python -m hydra_market_pipeline `
  --input data/raw/synthetic_market_events.csv `
  --aliases config/symbol_aliases.json `
  --output-dir build/demo
```

This is inspectable data-engineering evidence, **not** a claim of a live market-data runtime.

## Fail-closed validator sample

A focused public implementation example lives in [`t6-fail-closed-validator/`](t6-fail-closed-validator/). The component is explicitly **source-only, dormant, and not activated**; its public contract is fail-closed and returns only `ABSTAIN` or `QUARANTINE`.

- [`authority.py`](t6-fail-closed-validator/src/hydra_t6_failclosed/authority.py) validates the authority envelope, exact scope and digest bindings, time validity, revocation/supersession state, and signature trust.
- [`handoff.py`](t6-fail-closed-validator/src/hydra_t6_failclosed/handoff.py) validates candidate-only handoff semantics and rejects authority smuggling, including camelCase/PascalCase variants.
- [`receipt.py`](t6-fail-closed-validator/src/hydra_t6_failclosed/receipt.py) constructs deterministic inert receipts that keep canonical selection, canonical mutation, ML training, trading authorization, and external actions disabled.
- [`tests/`](t6-fail-closed-validator/tests/) covers signed authority envelopes, deterministic document handling, inert receipts, dormant integration, and authority-smuggling variants.

This is inspectable code evidence, **not** a claim that the validator is activated in a live production runtime.

### Reproduce the validator check

GitHub Actions runs the validator tests on Python 3.11 whenever the component or its workflow changes. From the component directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\\src').Path
python -m unittest discover -s tests -t . -v
```

[View the validator CI workflow →](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml)

## Engineering principles

- **Fail closed.** Missing authority produces a blocker, not a fabricated value.
- **Make lineage inspectable.** Important outputs should be traceable back to source and transformation authority.
- **Keep repairs bounded.** Fix the proven defect rather than redesigning adjacent architecture.
- **Separate evidence from claims.** Representative, synthetic, and live evidence are labeled differently.
- **Prefer deterministic replay.** Repeated validation should reproduce the same result from the same pinned inputs.
- **Protect canonical state.** Dry-run, immutability pins, quarantine, and release gates are used where mutation would be risky.

## Recruiter path

If you have 60 seconds:

1. Start with the **HYDRA project site**: https://hydradataai.github.io/Hydra-Website/
2. Open the **architecture** view for the end-to-end data flow.
3. Review the **case study** for a source → identity → authority → lineage → constraint walkthrough.
4. Open the **proof** section for validation, failure semantics, and engineering receipts.
5. Inspect [`market-data-pipeline-sample/`](market-data-pipeline-sample/) for a runnable ingestion → normalization → provenance → quarantine → Parquet path.

## Current scope

HYDRA is an actively developed engineering project. Public materials focus on inspectable architecture, data-contract behavior, provenance, and bounded technical proof.

The public surfaces do **not** claim:

- live autonomous trading;
- production ML deployment;
- fabricated production metrics;
- authority that the underlying producers cannot prove.

Future cloud and ML work stays in the roadmap until it is implemented and inspectable.

## Links

- **Project site:** https://hydradataai.github.io/Hydra-Website/
- **Website repository:** https://github.com/HYDRADATAAI/Hydra-Website
- **Core repository:** https://github.com/HYDRADATAAI/Hydra


## Maintenance guard

The public core repository is protected by deterministic CI. [Public repository validation](https://github.com/HYDRADATAAI/Hydra/actions/workflows/public-repository-validation.yml) checks required source/test paths, README links, public terminology, the validator's fail-closed `pyproject.toml` contract, and both Python 3.11 public-sample workflow contracts.
