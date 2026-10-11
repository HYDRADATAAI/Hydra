# HYDRA AWS Market-Data Vertical Slice

Status: **DEPLOYMENT ON HOLD / NOT DEPLOYED / SYNTHETIC / NON-LIVE**

This sample maps the public deterministic market-data pipeline onto a small AWS serverless path without claiming that the stack has already run in an AWS account.

## Flow

`synthetic CSV -> private raw S3 -> Python 3.11 Lambda -> accepted/quarantine/manifests S3 objects -> Glue partition commit -> bounded Athena query`

The Lambda transform performs strict file-contract validation, row normalization, deterministic event identity, provenance hashing, explicit quarantine, and deterministic manifest generation. It writes accepted JSONL, quarantine JSONL, and the manifest before registering a Glue partition for the accepted run. The partition is the Glue/Athena visibility commit on initial publication: if any artifact write fails before partition creation, Athena cannot query that run through `normalized_events`. A later failed retry does not withdraw a partition from an earlier successful publication. Replaying identical source bytes targets the same content-addressed object keys and emits the same bytes; an already registered partition is safe for that deterministic replay. The Lambda rejects source objects above the configurable 1 MiB default (2,000,000-byte hard maximum) and CSVs above 10,000 data rows before writing that object's artifacts. Direct S3 readers can still see an accepted object left by a failed later write, so they should require a manifest or Glue partition before consuming a run.

## AWS resources

- two private, encrypted, versioned S3 buckets with bounded retention;
- one S3-triggered Python 3.11 Lambda function;
- least-privilege object-level read/write permissions;
- one Glue database and partitioned external table over accepted JSONL only; Lambda registers each run partition only after all three artifacts are stored;
- one Athena workgroup with enforced encrypted output and a 1 GiB scan cutoff;
- one explicit CloudWatch log group with bounded retention.

The sample's 30-day S3 lifecycle expires artifact objects, while Glue partition metadata remains. This is suitable for the short-lived demonstration stack; a long-running deployment needs a partition-retention cleanup process to prevent stale catalog entries.

[`template.json`](template.json) is an AWS SAM/CloudFormation template. It does not create resources by itself.

## Directory map

```text
fixtures/synthetic_market_events.csv  public synthetic input
function/processor.py                 deterministic transform and artifacts
function/app.py                       S3 event and object-write adapter
tests/                                processor, Lambda, and IaC contracts
local_demo.py                         credential-free local replay
template.json                         SAM/CloudFormation infrastructure
```

## Run locally

Only Python 3.11 and the standard library are required.

```powershell
python -m unittest discover -s tests -t . -v
python local_demo.py --output-dir build/local
```

The committed fixture is expected to produce **3 accepted / 4 quarantined** rows. Local outputs are deterministic:

- `normalized_events.jsonl`
- `quarantine_records.jsonl`
- `manifest.json`

## CI and deployment gate

[AWS market data pipeline CI](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-pipeline.yml) runs unit tests and local deterministic replay without AWS credentials or network access.

[AWS market data deploy and verify](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-deploy.yml) remains a manual workflow, but its deployment job is disabled (`if: false`). It cannot configure AWS credentials, deploy a stack, publish deployment evidence, or run teardown.

The hold closes a check-then-deploy race: checking that a stack is absent does not reserve its name, so concurrent runs could both pass preflight. The deploy command uses `sam deploy --resolve-s3`; its SAM-managed artifact bucket may sit outside the CloudFormation stack, and the current teardown does not inventory or clean that external bucket. No AWS deployment is verified, and the disabled workflow produces no deployment artifact.

Keep the job disabled until create-only ownership is atomic; teardown proves ownership of the stack and each bucket before deletion, including after partial failure; the SAM artifact bucket has explicit safe ownership and cleanup; and no-AWS tests cover name collisions, partial failures, and ownership mismatches. External role trust, permissions, and environment approvals still require review in GitHub and AWS.

## Claim boundary

This sample is infrastructure and deterministic test evidence for a small synthetic vertical slice. It is not evidence of:

- a currently deployed AWS stack;
- production availability, scale, reliability, or cost;
- a production data lake or warehouse;
- live market-data ingestion;
- customer traffic, trading, or ML execution.

Website promotion should occur only after a successful manual deployment produces inspectable, sanitized evidence.
