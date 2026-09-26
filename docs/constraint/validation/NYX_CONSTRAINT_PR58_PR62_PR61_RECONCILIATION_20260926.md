# Constraint custody, outcome and shadow replay reconciliation

Base main: `eb45402f54d57f69fbbccb7cc21661bd088033c9`.

## Integrated scope

- PR #58 at `9ea283a7c4775543069a657a3c01684d92606692`: persisted custody and the network-blind private materializer, retained as Batch017.
- PR #62 at `e15909dcaf53518c09d3fa1be2423f3c13558492`: outcome supplement and assignment tracker, renumbered Batch018. Both branches had introduced the same Batch017 master and manifest paths. Batch018 follows custody Batch017 and retains its readiness declaration.
- PR #61 at `fc29f73debd9987b571eb7052da8be9424bd36f9`: only the shadow replay implementation, its two regression test files, and Lily's candidate temporal overlay are imported byte-for-byte. Full owner-seam and alternative acceptance-gate changes are not integrated.

Main's existing Batch001–Batch016 domain artifacts and PR58's Batch017 artifacts remain unchanged. The outcome supplement retains six records, four labels and the bounded coverage classification. Historical validators may still print their historical counts; the Batch018 outcome validator reports six.

## Replay repair

Candidate visibility requires candidate knowledge time and visible supporting claims. Dependent relief and beneficiary objects require visible parents and supporting lineage. Reference namespaces are checked; duplicate identities and naive timestamps fail closed. These checks apply to the existing normalized shadow fixture, not an ordinary replay admission of all six outcome records.

Batch011 snapshot receipts remain historical evidence for the predecessor algorithm. They are not proofs of the repaired algorithm. The imported tests reproduce the repaired temporal boundary and preserve predecessor receipts without rewriting them.

## Validation

- T6 test discovery: 149 tests pass, including 19 lineage regression methods.
- Private raw-store suite: 17 tests pass.
- Network-blind private materializer: 3 tests pass with synthetic inputs only.
- Outcome hostile matrix: 20 cases, including loss of inherited custody.
- Custody hostile matrix: 7 cases.
- Successor-chain hostile matrix: 19 cases.
- First-slice hostile matrix: 9 cases.
- Strict acceptance hostile matrix: 11 cases.
- Typed confidence hostile matrix: 9 cases.
- Successor chain, first-slice, outcome, custody, strict acceptance, typed confidence and public-repository validators pass locally.

## Remaining external work

Private raw capture is not executed. PR65's Windows acquisition path remains separate; its sanitized attestation must be produced by actual private execution. No source bytes, signed admission receipt, canonical constraint, qualified beneficiary or ordinary replay admission are created here.

PR61 cannot be merged wholesale without reconciling its alternative Batch014 document schema. This branch incorporates the bounded replay repair without replacing the sealed mainline gate. Existing PRs remain open and unchanged; this integration PR is the proposed combined path, not a claim that all parent PR work is merged.
