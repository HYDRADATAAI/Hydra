# Constraint closeout reconciliation — 2026-09-27

The separate closeouts are reconciled into PR #101. This is a bounded addition to its existing repair, with no PR merge and no change to main.

## Exact inputs

| Input | Commit |
| --- | --- |
| GitHub main, refreshed through the connector | `3cafc16f6a42a2eeeefa74f66a223ca8594374a9` |
| Common base / PR #96 | `794dcdc87f60bdfc4c67d72fec6ec771d0c46669` |
| PR #101 before reconciliation | `d12368a3660ee853828b55a5ca54423a22fca95d` |
| Separate audit integration | `d1bba524bf43755cc09c05dd645fc15d48f6721d` |

The source branches each had one unique commit above the common base. Their complete endpoint difference was inspected. The resulting commit is a normal continuation of PR #101; the audit branch remains an unchanged source checkpoint, not a second PR to merge independently.

## Resolutions

| Overlap or distinct change | Combined result |
| --- | --- |
| Audit capture-plan, attestation, and replay strict-field validation | Import its two runtime modules and two regression files byte-for-byte. Unexpected verification, private-path, or authority extensions are rejected. |
| Direct T1 backdating and T6 eligibility repairs | Already identical in both closeouts; retain unchanged. |
| Shared-batch successor discovery | Retain PR #101's implementation, including its nonempty slice check and same-scope ambiguity rejection. |
| Additional second-slice Batch017 hash mutation | Import the distinct hostile case; retain PR #101's first-slice and duplicate-scope cases. |
| Outcome timestamp authority | Retain all four PR #101 hostile cases and the source/outcome guards. The audit branch's absence of these changes must not undo them. |
| README, capture-template and PowerShell operational paths | Retain PR #101's corrections and the existing path-authority record. No Windows paths are accessed or moved. |
| README predecessor/intermediate/current binding | Retain PR #101's exact bindings, current-blob tests, and preserved prior README successor. No validator weakening. |
| Historical manifests and new runtime pins | Preserve the historical Batch017 private-record manifest. Append four exact predecessor/successor pairs to the existing first-slice Batch018 manifest; its regression validates each current successor blob. |
| Private supersession scope | Retain the T1-only map and existing central T6 transitions; do not duplicate T6 entries into the T1-only map. |
| Prior reports and historical fixture annotations | Preserve them. This report and its JSON companion describe the reconciled tree; earlier test counts remain historical. |

## Test-first evidence

Before importing the runtime repair, the audit regression files were run against the original PR #101 runtime. The 22-test focused suite produced 11 failing assertions, including subtests: unsupported metadata and authority extensions were accepted. With the two audit runtime modules imported, the same 22 tests passed.

The complete local queue then passed all 43 commands on Python 3.12.14:

- Integrated physical dependency, geopolitical policy, replay, T1 and T6: **338 tests and 459 subtests passed**.
- Standalone T1: **59 tests passed**.
- Outcome hostile suite: **24 cases passed**.
- Successor hostile suite: **22 cases passed**, including both Batch017 slices and duplicate same-scope rejection.
- First-slice integration, acceptance, confidence, custody, owner seams, and their hostile suites: **PASS**.
- Existing second-slice Batch017–029 validators and hostile suites: **PASS**; these validate committed artifacts and synthetic mutations, not live captures.
- Public repository validation and whitespace: **PASS**.

Additional checks: sanitized public attestation validation PASS; public-root hygiene PASS; all eight Batch016 JSON files byte-identical to refreshed main; all first/second-slice domain records, architecture records, workflows, outcome guards, strict successor implementations and README byte-identical to original PR #101. Four imported runtime/test blobs exactly match the audit branch. Source blob bindings and command summaries are in `NYX_CLOSEOUT_RECONCILIATION_VALIDATION_20260927.json`.

Hosted Python 3.11 workflow completion is verified after publication against the exact resulting head and reported in PR #101. Local completion alone is not hosted completion.

## Unchanged boundaries

`D_OWNER_GATE=BLOCKED`. Owner-gated first-slice work remains on HOLD. Eaton and GE Vernova remain `TIMESTAMP_UNVERIFIED`; their stored timestamp claims are not independently verified acquisition evidence. The nine-source public attestation receives structural validation only. Private bodies, private receipts, Windows execution and historical acquisition evidence were not inspected or certified.

No new capture, private evidence publication, receipt issuance, backdating, canonical admission, readiness promotion, production activation, authority expansion, or merge occurred. Native signed T5→T6 admission and full-run readiness remain blocked by their existing evidence and authority requirements.
