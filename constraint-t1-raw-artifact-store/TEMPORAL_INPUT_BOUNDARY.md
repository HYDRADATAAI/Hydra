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
