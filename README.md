# HYDRA

**Market Intelligence & Data Engineering System**

> Turn fragmented market data into traceable intelligence.

[![T6 fail-closed validator](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/t6-validator.yml)
[![Market data pipeline sample](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml)
[![SQL data quality sample](https://github.com/HYDRADATAAI/Hydra/actions/workflows/sql-data-quality-sample.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/sql-data-quality-sample.yml)
[![AWS market data pipeline sample](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-pipeline.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-pipeline.yml)
[![Governed context, retrieval, and grounding sample](https://github.com/HYDRADATAAI/Hydra/actions/workflows/governed-intelligence-sample.yml/badge.svg)](https://github.com/HYDRADATAAI/Hydra/actions/workflows/governed-intelligence-sample.yml)

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

`CSV + aliases → exact replay snapshots → contract check → normalization → deterministic identity → provenance → quarantine → JSONL / CSV → manifest v2`

The sample intentionally distinguishes **file-level contract drift** from **row-level data-quality defects**: incompatible file schemas fail the run, while malformed or duplicate rows are quarantined with machine-readable reason codes. Each run also emits two replayable, manifest-declared input snapshots: the exact seven-row synthetic source CSV and the canonical resolved alias map. `raw_record_sha256` commits the normalized mapping of the eight required CSV columns, not unexpected structural cells; the exact `source_snapshot.csv` commits every source byte, and independent replay verifies structural-extra quarantine outcomes.

It also includes a bounded local operations path:

`pinned partition plan → source-byte/partition budget → checkpointed runs → injected interruption → resume → SLI + recovery receipt`

The operations path proves atomic checkpoints, integrity-checked reuse, idempotent completed replay, deterministic recovery equivalence, complete row accounting, and structured metrics over two synthetic partitions. These are local implementation receipts, not production SLO or uptime measurements.

Key evidence:

- [`pipeline.py`](market-data-pipeline-sample/src/hydra_market_pipeline/pipeline.py) performs strict contract checks, normalization, deterministic event identity, provenance hashing, and quarantine decisions.
- [`writers.py`](market-data-pipeline-sample/src/hydra_market_pipeline/writers.py) emits deterministic JSONL, CSV, quarantine, exact source and resolved-alias snapshots, and manifest v2 artifacts.
- [`pipeline_manifest.schema.json`](market-data-pipeline-sample/contracts/pipeline_manifest.schema.json) fixes the two replayable input descriptors and three generated output descriptors.
- [`operations.py`](market-data-pipeline-sample/src/hydra_market_pipeline/operations.py) executes bounded backfills with atomic checkpoints, persisted-artifact verification, deterministic SLIs, and idempotent reuse.
- [`test_pipeline.py`](market-data-pipeline-sample/tests/test_pipeline.py) verifies expected accept/quarantine counts, deterministic reruns, CSV/JSONL equivalence, provenance, no silent data loss, and file-level contract failure.
- [`test_operations.py`](market-data-pipeline-sample/tests/test_operations.py) verifies interruption recovery, byte-identical clean/resumed outcomes, tamper rejection, changed-source rejection, budgets, row accounting, and completed replay.
- [Market data pipeline CI](https://github.com/HYDRADATAAI/Hydra/actions/workflows/market-data-pipeline.yml) runs the tests, executes the synthetic fixture, verifies the manifest, and publishes the generated outputs as a workflow artifact.

From the sample directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
python -m hydra_market_pipeline `
  --input data/raw/synthetic_market_events.csv `
  --aliases config/symbol_aliases.json `
  --output-dir build/demo
python run_recovery_demo.py --output-dir build/operations
```

This is inspectable data-engineering and local operational evidence, **not** a claim of a live market-data runtime or production operations.

## Public SQL data-quality sample

A bounded SQL example lives in [`sql-data-quality-sample/`](sql-data-quality-sample/). It uses **synthetic, non-live** records and SQLite to demonstrate relational data-engineering fundamentals:

`raw table → alias join → normalized view → CTE/window quality checks → accepted/quarantine views → analytical summary`

The sample includes joins, CTEs, `ROW_NUMBER`, `LAG`, windowed averages, grouped quality summaries, and Python-driven regression tests. It is intended as inspectable SQL/data-quality evidence, not as a production database or warehouse.

## AWS deployment-ready vertical slice

A bounded cloud mapping lives in [`aws-market-data-pipeline/`](aws-market-data-pipeline/). Its current status is **deployment-ready / not yet deployed / synthetic / non-live**.

`synthetic CSV → private raw S3 → Python 3.11 Lambda → accepted/quarantine S3 prefixes → Glue table → bounded Athena query`

The sample includes:

- [`template.json`](aws-market-data-pipeline/template.json), a SAM/CloudFormation template for encrypted private buckets, a least-privilege transform function, a Glue table over accepted outputs, and an Athena workgroup with a scan cutoff;
- [`processor.py`](aws-market-data-pipeline/function/processor.py), the deterministic transform shared by local replay and Lambda;
- [`test_processor.py`](aws-market-data-pipeline/tests/test_processor.py), [`test_lambda_handler.py`](aws-market-data-pipeline/tests/test_lambda_handler.py), and [`test_template.py`](aws-market-data-pipeline/tests/test_template.py) for data, adapter, replay, and infrastructure contracts;
- [credential-free CI](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-pipeline.yml) for local deterministic evidence;
- a [manual OIDC deploy-and-verify workflow](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-deploy.yml) that compares deployed S3 artifacts byte-for-byte with local replay, runs a bounded Athena query, publishes sanitized evidence, and tears the stack down by default.

No AWS deployment is claimed until that manual workflow succeeds against a real account. The website should not promote this path as deployed evidence before then.

## Governed context, retrieval, and structured grounding sample

A downstream control proof lives in [`governed-intelligence-sample/`](governed-intelligence-sample/). It consumes the exact synthetic artifacts emitted by the public market-data pipeline and demonstrates three boundaries before any model or agent execution:

`manifest integrity -> policy decision -> bounded accepted context -> exact citations -> deterministic evaluation receipt`

It also provides a transparent retrieval benchmark over the same accepted-only evidence:

`accepted records -> digest-bound closed-vocabulary lexical policy -> deterministic ranking -> exact citations -> separately specified qrels -> Recall@k / MRR receipt`

It also validates synthetic structured candidate claims after retrieval:

`governed retrieval -> synthetic structured candidate -> exact field/value/citation validation -> ADMIT / QUARANTINE / ABSTAIN / REFUSE receipt`

The sample freezes verified evidence and policy collections, derives citation filenames from the manifest, and fails closed on artifact drift, unresolved query terms, configured restricted terms, and non-ASCII/confusable queries. Quarantined raw rows never enter context or retrieval. Separately specified record-level qrels keep quality metrics apart from exact regression expectations. Structured candidates are admitted only when every allowed claim exactly matches the retrieved record and citation. Schema-valid candidate safety or grounding defects quarantine the entire candidate without claim leakage; clean candidates inherit retrieval `ABSTAIN` or `REFUSE` outcomes.

The upstream pipeline manifest v2 declares an exact `source_snapshot.csv` and canonical `resolved_symbol_aliases.json`. The 15-member deterministic proof package intentionally includes both replay inputs: all 7 rows are synthetic, including rows designed to quarantine, so governed loading can independently replay the complete fixture and require byte-identical normalized and quarantine outputs. Governed context, retrieval, and receipt artifacts remain accepted-only or aggregate-only and do not expose quarantined row payloads. This verifies declared-source provenance and quarantine outcomes for this fixture; it is not evidence about an undeclared or live source.

This is inspectable control, **lexical retrieval**, and structured-output validation evidence. Candidate responses are committed synthetic fixtures, not model output. It does **not** claim model execution or quality, semantic or embedding retrieval, natural-language intent or claim extraction, autonomous action, live market coverage, production performance, investment advice, or trading authorization.

Key evidence:

- [`context.py`](governed-intelligence-sample/src/hydra_governed_intelligence/context.py) verifies upstream digests, assembles bounded accepted-record context, and validates citations.
- [`evaluation.py`](governed-intelligence-sample/src/hydra_governed_intelligence/evaluation.py) emits deterministic decisions, evaluation results, and digest-bound receipts.
- [`retrieval.py`](governed-intelligence-sample/src/hydra_governed_intelligence/retrieval.py) applies accepted-only weighted lexical ranking with deterministic tie breaking and exact citations.
- [`retrieval_evaluation.py`](governed-intelligence-sample/src/hydra_governed_intelligence/retrieval_evaluation.py) evaluates exact outcomes separately from digest-bound record-level qrels.
- [`grounding.py`](governed-intelligence-sample/src/hydra_governed_intelligence/grounding.py) validates structured claims against retrieved records and exact citations before release.
- [`pipeline_replay.py`](governed-intelligence-sample/src/hydra_governed_intelligence/pipeline_replay.py) independently reconstructs accepted and quarantined records from the two manifest-declared input snapshots.
- [`pre_upload_verifier.py`](governed-intelligence-sample/src/hydra_governed_intelligence/pre_upload_verifier.py) verifies 9 manifested governed outputs, 26 receipts, 2 input snapshots, and 7 replayed source rows before building a deterministic 15-member proof ZIP.
- [`evaluation_cases.json`](governed-intelligence-sample/fixtures/evaluation_cases.json) makes the admit, abstain, and refuse expectations inspectable.
- [`retrieval_cases.json`](governed-intelligence-sample/fixtures/retrieval_cases.json) and [`retrieval_qrels.json`](governed-intelligence-sample/fixtures/retrieval_qrels.json) separate behavioral expectations from quality judgments.
- [`grounding_policy.json`](governed-intelligence-sample/config/grounding_policy.json) and [`grounding_cases.json`](governed-intelligence-sample/fixtures/grounding_cases.json) make allowed fields and fail-closed claim outcomes inspectable.
- [Governed intelligence CI](https://github.com/HYDRADATAAI/Hydra/actions/workflows/governed-intelligence-sample.yml) checks out the proposed revision, rebuilds its upstream synthetic artifacts, runs that revision's tests and deterministic contract checks, and publishes one packaged snapshot of the verified artifacts, reports, and receipts. It downloads the published artifact and compares the inner ZIP with the digest emitted by the packaging step. The run is repository-controlled evidence for that revision, not independent attestation of untrusted changes.

The proof ZIP byte size and SHA-256 are derived and reported by each successful integrated run; the source documentation does not predeclare a digest or size before those bytes exist. The ZIP is integrity-bound, but reproducing every receipt also requires the verification support files from the pinned repository revision.

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
5. Inspect [`market-data-pipeline-sample/`](market-data-pipeline-sample/) for a runnable ingestion → normalization → provenance → quarantine → deterministic artifact path.
6. Open its [`operations.py`](market-data-pipeline-sample/src/hydra_market_pipeline/operations.py) and recovery tests for checkpoint, backfill, replay, integrity, SLI, and budget behavior.
7. Inspect [`sql-data-quality-sample/`](sql-data-quality-sample/) for relational SQL, quality classification, joins, CTEs, and window functions.
8. Inspect [`aws-market-data-pipeline/`](aws-market-data-pipeline/) for the deployment-ready, not-yet-deployed S3 → Lambda → Glue/Athena mapping.
9. Inspect [`governed-intelligence-sample/`](governed-intelligence-sample/) for immutable verified context, hardened accepted-only lexical ranking, separately specified relevance judgments, exact citations, and synthetic structured-claim grounding.

## Current scope

HYDRA is an actively developed engineering project. Public materials focus on inspectable architecture, data-contract behavior, provenance, and bounded technical proof.

The public surfaces do **not** claim:

- live autonomous trading;
- a currently deployed or production-grade AWS data platform;
- production ML deployment;
- executed model or agent behavior in the public pre-model sample;
- fabricated production metrics;
- authority that the underlying producers cannot prove.

The AWS sample remains deployment-ready rather than deployed until a real manual run produces sanitized evidence. The governed-intelligence sample stops before model execution. Broader production cloud and ML work stays in the roadmap until it is implemented and inspectable.

## Links

- **Project site:** https://hydradataai.github.io/Hydra-Website/
- **Website repository:** https://github.com/HYDRADATAAI/Hydra-Website
- **Core repository:** https://github.com/HYDRADATAAI/Hydra


## Maintenance guard

[Public repository validation](https://github.com/HYDRADATAAI/Hydra/actions/workflows/public-repository-validation.yml) performs deterministic, repository-controlled conformance checks over required source/test paths, README links, public terminology, declared contracts, and Python 3.11 workflow structure. Because the validator and workflows are part of the checked revision, a passing run is reproducible self-evidence rather than an independent trust anchor against malicious repository code.
