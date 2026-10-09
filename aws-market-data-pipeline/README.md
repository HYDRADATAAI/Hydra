# HYDRA AWS Market-Data Vertical Slice

Status: **DEPLOYMENT-READY / NOT YET DEPLOYED / SYNTHETIC / NON-LIVE**

This sample maps the public deterministic market-data pipeline onto a small AWS serverless path without claiming that the stack has already run in an AWS account.

## Flow

`synthetic CSV -> private raw S3 -> Python 3.11 Lambda -> accepted/quarantine/manifests S3 objects -> Glue partition commit -> bounded Athena query`

The Lambda transform performs strict file-contract validation, row normalization, deterministic event identity, provenance hashing, explicit quarantine, and deterministic manifest generation. It writes accepted JSONL, quarantine JSONL, and the manifest before registering a Glue partition for the accepted run. The partition is the Glue/Athena visibility commit: if any artifact write fails, Athena cannot query that run through `normalized_events`. Replaying identical source bytes targets the same content-addressed object keys and emits the same bytes; an already registered partition is safe for that deterministic replay. Direct S3 readers can still see an accepted object left by a failed later write, so they should require a manifest or Glue partition before consuming a run.

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

[AWS market data deploy and verify](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-deploy.yml) is manual-only and restricted to `main`. It requires an `aws-demo` GitHub environment containing an `AWS_DEMO_ROLE_ARN` secret for OIDC federation. The workflow accepts only the reserved demo stack-name prefix and refuses to update an existing stack. Cleanup runs only after that invocation marks its own deployment attempt; teardown defaults to enabled. The SAM-managed deployment artifact bucket can remain outside the stack and must be checked separately. The external role trust policy, permissions, and environment approval rules must be reviewed in GitHub/AWS; repository contents cannot verify them. A run:

The AWS role trust policy should be scoped to this repository and the `aws-demo` environment. Its permissions should be limited to deploying and deleting this sample's prefixed CloudFormation, IAM, Lambda, S3, Glue, Athena, and CloudWatch Logs resources.

1. validates, builds, and deploys the SAM stack;
2. uploads the public synthetic fixture;
3. waits for accepted, quarantine, and manifest objects;
4. byte-compares deployed outputs with the local deterministic replay;
5. executes a bounded Athena aggregation;
6. publishes sanitized verification evidence as a workflow artifact;
7. tears the stack down by default, including versioned S3 objects.

Each invocation appends its GitHub run ID and attempt to the supplied stack name, then derives stable, globally unique bucket names from the AWS account, region, and resulting stack name. Teardown verifies the per-run ownership tag and CloudFormation resource bindings, and deletes only buckets recorded as resources of that stack. It handles failed creates as well as successful runs, and paginates versioned-object deletion. Bucket names remain outside the published evidence artifact, and the configured action masks the account identifier in workflow logs.

The deploy workflow is not evidence until it completes successfully against a real AWS account. No repository secret, account identifier, bucket name, or role ARN is committed here.

## Claim boundary

This sample is infrastructure and deterministic test evidence for a small synthetic vertical slice. It is not evidence of:

- a currently deployed AWS stack;
- production availability, scale, reliability, or cost;
- a production data lake or warehouse;
- live market-data ingestion;
- customer traffic, trading, or ML execution.

Website promotion should occur only after a successful manual deployment produces inspectable, sanitized evidence.
