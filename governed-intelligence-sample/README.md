# Governed intelligence context, retrieval, and structured grounding

This runnable sample proves three deterministic boundaries before any model or agent execution:

`integrity-checked pipeline artifacts -> policy decision -> bounded context -> exact citations -> evaluation receipt`

`accepted records only -> hardened lexical ranking -> exact citations -> separately specified qrels -> retrieval benchmark`

`governed retrieval -> synthetic structured candidate -> exact claim/citation validation -> grounding receipt`

It consumes the **synthetic, non-live** artifacts from [`market-data-pipeline-sample/`](../market-data-pipeline-sample/). It does not call a model, vector database, broker, or external service.

## What it proves

- every upstream artifact is checked against its manifest SHA-256 before use;
- manifest v2 binds an exact source CSV snapshot and canonical resolved-alias snapshot;
- `raw_record_sha256` commits the normalized mapping of the eight required CSV columns, not unexpected structural cells; the exact source snapshot commits every source byte;
- an independent replay reconstructs all seven accepted or quarantined source rows and requires byte-identical pipeline outputs;
- verified evidence and retrieval-policy collections are immutable after loading;
- citations use the accepted artifact filename declared by the verified manifest;
- governed context, retrieval, and receipt artifacts are accepted-only or aggregate-only and never expose quarantined row payloads;
- missing evidence produces `ABSTAIN`, while trading or restricted-corpus requests produce `REFUSE`;
- retrieval v2 uses integer field weights, deterministic event-ID tie breaking, and a digest-bound closed vocabulary;
- unresolved terms cannot borrow score from valid metadata, and non-ASCII/confusable queries fail closed;
- exact ranking expectations and independently hashed record-level relevance judgments are separate inputs;
- fixture-bounded Recall@k and MRR are computed from separately specified qrels, not from expected rankings;
- structured claims must match an allowed field, exact retrieved value, record, and citation;
- any schema-valid candidate safety or grounding defect produces `QUARANTINE` without releasing candidate claims or citations; structurally invalid input fails closed without a receipt;
- decisions bind their governing policy and pipeline evidence, while evaluation reports additionally bind fixtures and qrels; and
- model execution and external actions remain unauthorized and `NOT_EXECUTED`.

The retrieval benchmark contains 13 cases: 4 `ADMIT`, 6 `ABSTAIN`, and 3 `REFUSE`. Six quality cases with separately specified record-level qrels produce micro Recall@k `0.444444`, macro Recall@k `0.583333`, and MRR `0.666667`; the deliberately strict threshold exposes misses rather than hiding them. The grounding benchmark contains 8 cases: 1 `ADMIT`, 5 `QUARANTINE`, 1 `ABSTAIN`, and 1 `REFUSE`.

## What it does not prove

This is deterministic control, **lexical** retrieval, and structured-output validation evidence. The candidate responses are committed synthetic fixtures, not model output. There is no model inference, natural-language claim extraction, semantic or embedding retrieval, model-quality evidence, live market coverage, production latency or uptime, autonomous action, investment advice, or trading authorization.

The context path uses explicit structured task types. Retrieval accepts only indexed evidence terms plus an explicit non-scoring vocabulary. Those constraints are intentionally narrow and must not be represented as general natural-language understanding.

## Run it

From the repository root, first produce the governed upstream artifacts:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\market-data-pipeline-sample\src').Path
python -m hydra_market_pipeline `
  --input market-data-pipeline-sample/data/raw/synthetic_market_events.csv `
  --aliases market-data-pipeline-sample/config/symbol_aliases.json `
  --output-dir market-data-pipeline-sample/build/demo
```

Then run the tests and all three evaluations:

```powershell
Set-Location governed-intelligence-sample
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
python run_demo.py `
  --pipeline-output-dir ../market-data-pipeline-sample/build/demo `
  --policy config/policy.json `
  --cases fixtures/evaluation_cases.json `
  --output-dir build/evaluation
python run_retrieval_demo.py `
  --pipeline-output-dir ../market-data-pipeline-sample/build/demo `
  --policy config/retrieval_policy.json `
  --cases fixtures/retrieval_cases.json `
  --qrels fixtures/retrieval_qrels.json `
  --output-dir build/retrieval
python run_grounding_demo.py `
  --pipeline-output-dir ../market-data-pipeline-sample/build/demo `
  --retrieval-policy config/retrieval_policy.json `
  --grounding-policy config/grounding_policy.json `
  --cases fixtures/grounding_cases.json `
  --output-dir build/grounding
```

The context evaluation writes `decisions.jsonl`, `evaluation_report.json`, and `output_manifest.json`.

The retrieval benchmark writes:

- `retrieval_decisions.jsonl`: verified decisions, integer scores, and exact citations;
- `retrieval_evaluation_report.json`: behavioral controls, independent quality metrics, citation counts, and zero-execution counters;
- `retrieval_output_manifest.json`: SHA-256 bindings for receipts, policy, suite, qrels, and upstream artifacts.

The grounding benchmark writes:

- `grounding_receipts.jsonl`: claim-level validation results and fail-closed dispositions;
- `grounding_evaluation_report.json`: expected/actual outcomes and execution/action safety counters;
- `grounding_output_manifest.json`: SHA-256 bindings for grounding outputs and all input contracts.

GitHub Actions checks out the proposed revision, rebuilds its synthetic upstream evidence, and runs that revision's tests and deterministic contract checks. The final verifier confirms 2 manifest-declared input snapshots and 7 independently replayed source rows, recomputes retrieval metrics from qrels and verified decisions, derives grounding totals from verified receipts, and packages the validated byte snapshots for upload.

## CI evidence scope

The workflow publishes one deterministic, uncompressed 15-member ZIP containing the exact generated artifact snapshots read by the final verifier. It intentionally includes the exact `source_snapshot.csv` with all 7 synthetic rows, including rows designed to quarantine, plus the canonical `resolved_symbol_aliases.json`, so independent replay can verify structural-extra quarantine outcomes and byte-identical outputs from complete declared inputs. Governed context, retrieval, and receipt artifacts remain accepted-only or aggregate-only and do not expose quarantined row payloads. The verifier keeps the governed count at 9 manifested outputs and 26 receipts while separately reporting `INPUT_SNAPSHOTS_VERIFIED=2` and `SOURCE_ROWS_REPLAYED=7`. Archive member paths, ordering, timestamps, permissions, compression mode, and contents are fixed and tested; the upload step selects only that package. The workflow then downloads the published artifact and requires its inner ZIP digest to match the packaging step's output. This binds every passing run to the packaged payload and removes mutable source directories from the upload selection.

The integrated run computes the final ZIP byte size and SHA-256 from the actual 15 members. They are intentionally not hardcoded here before integration regenerates the bound artifacts.

The ZIP is integrity-bound, but reproducing every receipt also requires the verification support files from the pinned repository revision.

The workflow, verifier, and validator are all code from the proposed revision. Their passing run is reproducible, repository-controlled evidence for that revision, not independent attestation or a trust anchor against malicious repository code.
