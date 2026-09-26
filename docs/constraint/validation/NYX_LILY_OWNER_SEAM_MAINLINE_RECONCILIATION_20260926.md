# Lily owner-seam conformance on sealed mainline acceptance

Base: PR #68, commit `451f1fd3f6d7e3b071caa2248d6fc181f658373c`.
Owner-seam implementation source: PR #61, commit
`fc29f73debd9987b571eb7052da8be9424bd36f9`, carrying Lily's owner work.

## Repair

The proposed owner-seam validator expected an alternative Batch014 document
using `gates`, `strict_gate_result` and `overall_result`. The sealed mainline
Batch014 contract uses `dimensions`, `status` and `overall_status`. Importing
the alternative document would rewrite domain history and break its manifest.

This change imports the conformance module, CLI and tests, adapting their gate
checks to the existing mainline contract. It preserves Lily's candidate temporal
overlay from PR #68 and its exact Batch010 predecessor pin. No domain artifact,
master, outcome record, confidence value, threshold or sealed manifest is edited.

Both native binding and canonical constraint/beneficiary admission must remain
explicit blockers under `IMPLEMENTATION_ADMITTED`. Provenance and replay must
remain BLOCKED, and run denials must be explicit. The validator rejects the
competing legacy gate representation rather than allowing conflicting fields.
The historical gate remains a historical conformance input, not a replacement
for current Batch018 acceptance validation.

## Validation

- 166 T6 tests PASS under both supported discovery modes, including 17 owner-seam
  test methods. The added cases exercise missing/ready dimensions, conflicting
  representations, incorrect schema/identity, missing admission blockers and
  missing or permissive run declarations.
- Owner-seam CLI PASS: 10 claims, 3 T5 candidates, 4 T6 beneficiary evaluations,
  0 canonical constraints and 0 qualified beneficiaries.
- Successor-chain, current outcome, historical strict acceptance and public
  repository validators PASS.
- Every predecessor domain file is byte-identical to PR #68's tested base.
- Existing integration CI now runs the owner-seam CLI; T6 CI discovers the new
  regression tests automatically.

## Remaining boundary

This closes the repo-side owner-seam validator/schema integration mismatch. It
does not issue native signed admission, execute private capture, admit ordinary
replay or canonically qualify a constraint or beneficiary. It does not claim to
integrate all private-record/materialization work in PR #56 or all alternative
gate/audit artifacts in PR #61. PR #65 remains a separate local execution path.

This PR is stacked on #68. Review and integrate the parent first; do not merge the
competing Batch014 document merely to make the older validator pass.
