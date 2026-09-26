# HYDRA AWS Market-Data Vertical Slice

Status: **DEPLOYMENT-READY / NOT YET DEPLOYED / SYNTHETIC / NON-LIVE**

This sample maps the public deterministic market-data pipeline onto a small AWS serverless path without claiming that the stack has already run in an AWS account.

## Flow

`synthetic CSV -> private raw S3 -> Python 3.11 Lambda -> accepted/quarantine S3 prefixes -> Glue table -> bounded Athena query`

The Lambda transform performs strict file-contract validation, row normalization, deterministic event identity, provenance hashing, explicit quarantine, and deterministic manifest generation. Replaying identical source bytes targets the same content-addressed object keys and emits the same bytes.

## AWS resources

- two private, encrypted, versioned S3 buckets with bounded retention;
- one S3-triggered Python 3.11 Lambda function;
- least-privilege object-level read/write permissions;
- one Glue database and external table over accepted JSONL only;
- one Athena workgroup with enforced encrypted output and a 1 GiB scan cutoff;
- one explicit CloudWatch log group with bounded retention.

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

[AWS market data deploy and verify](https://github.com/HYDRADATAAI/Hydra/actions/workflows/aws-market-data-deploy.yml) is manual-only. It requires an `aws-demo` GitHub environment containing an `AWS_DEMO_ROLE_ARN` secret for OIDC federation. A run:

The AWS role trust policy should be scoped to this repository and the `aws-demo` environment. Its permissions should be limited to deploying and deleting this sample's prefixed CloudFormation, IAM, Lambda, S3, Glue, Athena, and CloudWatch Logs resources.

1. validates, builds, and deploys the SAM stack;
2. uploads the public synthetic fixture;
3. waits for accepted, quarantine, and manifest objects;
4. byte-compares deployed outputs with the local deterministic replay;
5. executes a bounded Athena aggregation;
6. publishes sanitized verification evidence as a workflow artifact;
7. tears the stack down by default, including versioned S3 objects.

The deploy workflow is not evidence until it completes successfully against a real AWS account. No repository secret, account identifier, bucket name, or role ARN is committed here.

## Claim boundary

This sample is infrastructure and deterministic test evidence for a small synthetic vertical slice. It is not evidence of:

- a currently deployed AWS stack;
- production availability, scale, reliability, or cost;
- a production data lake or warehouse;
- live market-data ingestion;
- customer traffic, trading, or ML execution.

Website promotion should occur only after a successful manual deployment produces inspectable, sanitized evidence.
