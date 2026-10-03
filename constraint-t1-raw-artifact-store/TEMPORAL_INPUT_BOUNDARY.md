# Generic lineage input boundary

The generic v1 source and evidence lineage builders accept the metadata fields
used by the existing Batch031/032/033/034 pipeline. Unsupported input fields
are rejected before normalization, including on excluded evidence records and
direct validator/selector calls. An explicitly supplied attestation member
disposition must be `ELIGIBLE`; a contradictory disposition cannot be rewritten.

This closes a demonstrated input-erasure defect. In particular, an added
`acquisition_verification_status=TIMESTAMP_UNVERIFIED`, a claimed verified
timestamp, or an unknown authority envelope cannot disappear while a normalized
packet is emitted. No positive timestamp-proof extension is accepted.

The existing metadata-only path still accepts legacy inputs without such
extensions. Its readiness/eligibility fields, matching hashes, equal acquisition
and availability times, and maximum-of-times calculation do not establish
trusted temporal authority. This repair does not close that broader dependency
or supply an admission gate for legacy inputs with no verification status.
Consumers must not interpret those legacy fields as verified historical proof.

`TRUSTED_TIMESTAMP_VERIFIER=NOT_IMPLEMENTED`

`REQUIRED_TRUST_ROOT=ABSENT_IN_AUDITED_PUBLIC_REPOSITORY`

`PIT_002B=OPEN`

Eaton and GE Vernova remain `TIMESTAMP_UNVERIFIED`. The rule requires independent
evidence binding an exact version to availability by its governed historical
cutoff. No approved proof encoding, designated independent timestamp source,
temporal trust anchor, executable verifier, or qualifying exact-version witness
is added. A new capture, hash, signature, commit, or receipt cannot substitute
for the missing earlier observation. No historical evidence records are edited.

Tests use synthetic fixtures and execute on hosted Windows. Their results prove
the bounded input rejection behavior, not historical source availability.

## Consistency of declared metadata

Builders, direct validators and selectors must apply the same required-value
checks. Evidence source IDs and origin artifacts must be nonempty strings;
matching a malformed input to an equally malformed output is insufficient.
An explicitly supplied valid-receipt count must be an integer matching the
active source count. Legacy omission remains supported.

Release creation cannot precede the latest declared acquisition, including on
imported public attestations and direct replay validation. Availability tables
must contain exactly the distinct availability instants. Equivalent timezone
or fractional-second spellings share one transition; original member timestamp
literals remain unchanged. These checks establish internal consistency only.

The first-slice path preserves the merged PR119 timestamp containment.
Recorded boundaries keep empty eligible-source lists, ordinary readiness stays
false, and V1 selection rejects unverified timestamps. The consistency checks
above do not grant admission. Generic Batch033/034 metadata behavior remains
separate from this first-slice denial.
