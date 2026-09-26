# HYDRA Constraint AI/data-center/power — Pass 004

Status: **VERTICAL_INTEGRATION_THIN**. V1 remains unfrozen.

## Reason for this pass

The former Batch016 custody branch was force-updated upstream from `cb866ead19948942558b926f11925bf54e1741b4` to `cc964c2aa73047e45ceeca236ec627b6e39ce1f6`. Main now contains the outcome-coverage Batch016 (`eb45402`), while custody is explicitly Batch017. PR59's previous base therefore ceased to match its tested authority history.

This pass consumes the declared Batch017 base at `cc964c2aa73047e45ceeca236ec627b6e39ce1f6` and reapplies the exact integration delta from old custody base `cb866ead19948942558b926f11925bf54e1741b4` to repair commit `53999337d722b3b20adb6e3b2105b615d860934c`. The prior candidate commits and reports remain in Git history; their recorded test results are not rewritten into claims about the current base.

## Concrete reconciliation

The only patch conflict was the first-slice CI workflow. It was resolved by retaining all upstream outcome/custody validation and hostile-test steps AND the existing owner-seam step. The combined-owner workflow additionally runs the existing outcome and custody validators.

All docs already present at the declared Batch017 base remain byte-for-byte unchanged. No current Batch016 outcome artifact is replaced by the obsolete custody candidate. No new source, outcome, capacity field, confidence policy, canonical identity or admission receipt is introduced.

The existing physical/policy/replay packages, point-in-time repair and mainline-compatible owner-seam checks are preserved. This is integration into the existing stack, not a new runtime architecture.

## Executed validation

- Combined five-package suite: **282 tests and 427 subtests passed**.
- First-slice integration, owner-seam conformance, outcome coverage, persisted custody, and NYX successor-chain checks: PASS.
- Outcome hostile matrix: **10 PASS**.
- Custody hostile matrix: **7 PASS**.
- Successor chain resolves to Batch017; 15 manifests / 113 members verified.
- Remote CI is not inferred from local results; inspect the exact published commit.

## Updated evidence readiness

Upstream Batch016 now supplies five real outcome records, four labels, and all three bounded core outcome dimensions. Its validator reports one substitution-success outcome and two beneficiary-capture observations. Those evidence observations do not create qualified T6 beneficiary relationships: the candidate and beneficiary gates still return zero canonical constraints and zero qualified beneficiaries.

The existing first-slice acceptance gate reports **zero repo-executable acceptance blockers**. This is bounded first-slice readiness, not completion of all 57 requested vertical areas or a grant of runtime authority.

## Actual remaining dependencies

The Batch017 master retains:

1. exact signed native T5→T6 admission;
2. private materialization of the real nine-source raw bodies;
3. complete source-version hashes and ordinary point-in-time eligibility;
4. canonical output/evaluation gates derived from those dependencies.

Broader named facility, accelerator/HBM/packaging, water/cooling and query coverage from Pass001 remains incomplete. No claim that ordinary historical replay or the complete requested geography→compute→constraint→beneficiary→outcome traversal is governed is justified yet.

Further repetition of taxonomy, confidence scaffolding or artificial evidence cannot close these external gates. The next acceptance execution belongs to the established private source-custody and native-admission paths. This pass does not perform a public merge, activation, canonical promotion or V1 freeze.
