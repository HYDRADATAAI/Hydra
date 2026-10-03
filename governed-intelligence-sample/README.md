# Governed intelligence pre-model sample

This runnable sample proves the boundary immediately before any model or agent execution:

`integrity-checked pipeline artifacts -> policy decision -> bounded context -> exact citations -> deterministic evaluation receipt`

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

## What it does not prove

This is a pre-model control and evaluation proof. It is not evidence of model quality, semantic retrieval quality, live market coverage, production latency or uptime, autonomous analysis, investment advice, or trading authorization.

The request fixture uses explicit structured task types. It does not pretend that natural-language intent classification has been implemented.

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
```

The evaluation writes:

- `decisions.jsonl`: one policy decision and, where admitted, its bounded context packet;
- `evaluation_report.json`: expected/actual control results and explicit zero-execution counters;
- `output_manifest.json`: SHA-256 bindings for the generated receipts and all input contracts.

GitHub Actions repeats this chain from the committed synthetic CSV and publishes the generated receipts as a workflow artifact.
