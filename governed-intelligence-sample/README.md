# Governed intelligence pre-model context and retrieval

This runnable sample proves two boundaries immediately before any model or agent execution:

`integrity-checked pipeline artifacts -> policy decision -> bounded context -> exact citations -> deterministic evaluation receipt`

`accepted records only -> weighted lexical ranking -> exact citations -> deterministic retrieval benchmark`

It consumes the **synthetic, non-live** accepted/quarantine outputs and manifest produced by [`market-data-pipeline-sample/`](../market-data-pipeline-sample/). It does not call a model, a vector database, a broker, or any external service.

## What it proves

- every upstream artifact is checked against its manifest SHA-256 before use;
- admitted observation context contains accepted records only and one resolvable citation per record;
- aggregate quality context reports quarantine counts without exposing quarantined raw rows;
- missing governed evidence and unsupported production metrics produce `ABSTAIN`;
- trading instructions produce `REFUSE`;
- every decision binds the exact policy and pipeline manifest digests;
- model execution remains `authorized: false` and `status: NOT_EXECUTED`;
- the five-case evaluation and all output receipts are byte-deterministic.
- lexical retrieval indexes accepted records only and never indexes quarantine details;
- ranking uses an inspectable field-weight policy, integer scores, and deterministic event-ID tie breaking;
- every ranked record carries an exact artifact, record ID, and record SHA-256 citation;
- the six-case retrieval benchmark reports Recall@k and mean reciprocal rank alongside abstain/refuse checks;
- unknown and quarantined-only symbols produce `ABSTAIN`, while requests for restricted raw/quarantine material produce `REFUSE`.

## What it does not prove

This is a pre-model control and **lexical** retrieval evaluation proof. It is not evidence of model quality, semantic or embedding retrieval quality, live market coverage, production latency or uptime, autonomous analysis, investment advice, or trading authorization.

The context fixture uses explicit structured task types. Retrieval tokenizes bounded fixture queries and applies a fixed, digest-bound weighting policy. Neither path pretends that natural-language intent classification has been implemented.

## Run it

From the repository root, first produce the governed upstream artifacts:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\market-data-pipeline-sample\src').Path
python -m hydra_market_pipeline `
  --input market-data-pipeline-sample/data/raw/synthetic_market_events.csv `
  --aliases market-data-pipeline-sample/config/symbol_aliases.json `
  --output-dir market-data-pipeline-sample/build/demo
```

Then run the tests and evaluation:

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
  --output-dir build/retrieval
```

The evaluation writes:

- `decisions.jsonl`: one policy decision and, where admitted, its bounded context packet;
- `evaluation_report.json`: expected/actual control results and explicit zero-execution counters;
- `output_manifest.json`: SHA-256 bindings for the generated receipts and all input contracts.

The retrieval benchmark writes:

- `retrieval_decisions.jsonl`: ranked accepted records, integer scores, and exact citations;
- `retrieval_evaluation_report.json`: six expected/actual decisions plus Recall@k, MRR, and zero-execution counters;
- `retrieval_output_manifest.json`: SHA-256 bindings for the retrieval receipts, policy, suite, and upstream manifest.

GitHub Actions repeats this chain from the committed synthetic CSV and publishes the generated receipts as a workflow artifact.
