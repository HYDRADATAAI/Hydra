# Public Claim Boundaries

HYDRA should be easier to trust because its public claims are narrower than its internal ambitions.

## Real observed data

Claims in this category must be traceable to an actual source or captured dataset.

## Derived data

Derived values must identify:
- the source data;
- the derivation;
- the component or contract that owns the derivation;
- enough information to reproduce it.

## Synthetic and shadow validation

Synthetic fixtures are useful for:
- schema testing;
- adversarial testing;
- deterministic serialization checks;
- contract seam testing;
- failure injection.

Synthetic evidence is not presented as proof of real-world trading performance.

## Research outputs

Backtests, offline analysis, labeling, and model-development artifacts should be labeled as research outputs unless a separate production claim is explicitly proven.

## Planned or incomplete integration

Architecture diagrams may show intended interfaces. A diagram is not evidence that every lane is live.

Public language should distinguish:
- implemented;
- validated;
- parked;
- blocked;
- planned.

## Cloud deployment boundary

The public AWS sample may be described as **deployment-ready** when its local tests, infrastructure contract tests, and credential-free CI pass.

It may be described as **deployed and verified** only after the manual AWS workflow succeeds against a real account and publishes sanitized evidence that proves:

- the stack deployed;
- the synthetic source object triggered the transform;
- accepted, quarantine, and manifest objects matched local deterministic replay;
- the bounded Athena query succeeded;
- no account identifier, role ARN, credential, or globally unique bucket name was disclosed.

Infrastructure code alone is not proof of a live AWS deployment, production scale, production availability, or production cost behavior.

## Operational evidence boundary

The checkpoint, backfill, recovery, SLI, and budget artifacts in the public market-data sample are deterministic local evidence over synthetic fixtures.

They may demonstrate implementation behavior such as atomic checkpointing, idempotent replay, tamper detection, complete row accounting, and bounded input execution. They are not production SLO measurements, uptime evidence, incident-response history, production cost observations, or proof of a deployed orchestration service.

## Pre-model intelligence boundary

The governed-intelligence sample is deterministic local evidence over synthetic pipeline artifacts. It may demonstrate:

- manifest and artifact integrity checks;
- policy-bound context assembly from accepted records;
- exact record and artifact citations;
- aggregate quality context that does not expose quarantined raw rows;
- explicit `ADMIT`, `ABSTAIN`, and `REFUSE` decisions;
- deterministic control-evaluation receipts.

The sample keeps model execution disabled. It is not evidence of model quality, semantic retrieval quality, natural-language intent classification, production inference, autonomous analysis, investment advice, or trading authorization.

## Trading boundary

HYDRA public materials should not imply autonomous live trading unless that state is separately and explicitly proven.

The public repository is an engineering portfolio and research artifact, not investment advice.
