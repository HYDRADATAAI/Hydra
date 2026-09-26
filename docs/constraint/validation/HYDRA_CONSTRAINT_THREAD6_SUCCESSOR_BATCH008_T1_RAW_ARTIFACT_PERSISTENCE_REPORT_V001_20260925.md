# HYDRA CONSTRAINT — Thread 6 Successor Batch 008 Private Raw Artifact Persistence

Predecessor: Batch 007  
Owner: PIPELINE_T1_SOURCE_ACQUISITION  
Result: PASS_MECHANISM_READY_REAL_CAPTURE_STILL_BLOCKED

Batch 008 implements the missing T1 raw-artifact persistence mechanism without
publishing raw third-party source bodies into the public repository.

## Implemented

- private raw-data root outside the public repo;
- SHA-256 content-addressed objects;
- atomic immutable writes;
- immutable source-version receipts;
- exact byte-length/digest verification;
- deterministic T1 release manifests;
- manifest membership enforcement;
- explicit eligible/quarantined/ineligible processing disposition;
- ordinary T1-to-T2 eligibility check;
- CLI for persisting an already-captured local file;
- no network acquisition.

## Blocker decomposition

PIT-002 is no longer one vague blocker.

- PIT-002A-PRIVATE-RAW-ARTIFACT-PERSISTENCE-MECHANISM -> CLOSED.
- PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION -> OPEN / BLOCKING ORDINARY REPLAY.

The current GitHub/public execution surface does not expose a mounted private
HYDRA raw-data root, so this pass does not claim that the nine real source
bodies have been durably materialized.

## Safety boundary

The store does not fetch URLs and therefore does not grant live-source authority.
It rejects private-store roots placed inside the public Git repository.

No raw source content was added to Git.

THREAD6_SUCCESSOR_BATCH008=PASS
PRIVATE_RAW_STORE_IMPLEMENTED=YES
CONTENT_ADDRESSED_IMMUTABLE_WRITE=YES
SOURCE_VERSION_RECEIPT_READY=YES
T1_RELEASE_MANIFEST_READY=YES
ORDINARY_T2_ELIGIBILITY_CHECK_READY=YES
NETWORK_ACQUISITION_AUTHORIZED=NO
PUBLIC_RAW_SOURCE_CONTENT_PUBLISHED=NO
NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED=NO
STRICT_ORDINARY_ORIGINAL_AS_OF_READY=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_POPULATION_BLOCKER=PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION
