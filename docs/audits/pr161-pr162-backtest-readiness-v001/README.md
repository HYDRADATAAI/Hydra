# PR161 + PR162 backtest-readiness audit V001

`AUDIT_STATUS=COMPLETE_STATIC_REVIEW`

`EMPIRICAL_BACKTEST_READINESS=BLOCKED`

`CALIBRATED_CASES=0`

`UNSEEN_HOLDOUT_CASES=0`

The validated replay/query stack supports reproducible retrospective classification. It does not yet establish predictive accuracy, calibrated probabilities, market lead time, or trading returns. This audit records the precise boundary, a case inventory, a versioned evaluation protocol, and bounded implementation risks. It makes no runtime, evidence, or admission changes.

## Frozen scope

| Input | Exact identity |
|---|---|
| Repository | HYDRADATAAI/Hydra |
| Main at audit start | `adaab38e2e2f53c381aa4d2baff38644be92e3d0` |
| Audited joint candidate | `e4eb1d95c82484a1518dcf037c8d0a99145231bc` |
| Audited tree | `62d4cdfb1f02d8bc31273711c513c765b030de17` |
| PR161 source head | `798ab329eea6c5ef937a04ebd69fc6651df2c5fe` |
| PR162 source head | `647ec1ba74c8f74c1f632fc1f5823fc60c003247` |
| Existing compatibility proof | [PR256](https://github.com/HYDRADATAAI/Hydra/pull/256), with [PR257](https://github.com/HYDRADATAAI/Hydra/pull/257) exact-source supplement |

Five parallel audits examined scoring, corpus evidence, temporal provenance, evaluation design, and test coverage. All observations are bound to the tree above. Source code was read, and governed JSON/JSONL bytes were joined using standard data-processing tools. No HYDRA module was imported or executed for this audit; no tests, model training, private-byte verification, capture, or external acquisition were performed. Prior CI results remain the compatibility evidence and are not new backtest results.

The audit timestamp is not a historical source-availability timestamp. [Input identities](input_freeze.json) record exact Git blobs and SHA-256 hashes.

## What the existing cases establish

| Measure | Observed inventory | Permitted interpretation |
|---|---:|---|
| Case families | 22 | Retrospectively classified development evidence |
| Availability cuts | 82 | Case-local availability snapshots, not independent prediction trials |
| Partial realizations | 17 | Supported mechanism/direction classification with limits |
| Unevaluable cases | 5 | Incomplete horizons or open contradictions; preserve their status |
| Admissible numeric confidence | 0 | Calibration remains blocked; Brier remains null |
| Explicit numeric success targets in mapping records | 0 | No retrospective full-target accuracy claim |
| Explicit horizons in mapping records | 1 | CHIPS has an incomplete long-horizon window |
| Unseen validation/test/prospective cases | 0 | All 22 examined cases are development-only |

All 22 selected confidence records are qualitative expectations, risks, objectives, or an operational commitment. None establishes a historically grounded numeric probability. A well-defined categorical target can support binary evaluation without a numeric magnitude or probability; the missing frozen prediction, endpoint, cohort and adjudication prerequisites still block that claim here. The mapping declarations were recorded in September 2026 after the historical outcome observations. Sourced historical narratives are not frozen HYDRA predictions made before those outcomes.

The cutoff alignment matters: 39 original cuts precede the selected hypothesis metadata and six are on or after the selected outcome observation. The remaining 37 are metadata-timing-compatible candidates only; they still lack the prerequisites for predictive performance measurement. Only one classified-case anchor matches an original availability cut. This does not show leakage in the existing availability replay: each cut admits its own allowed event inventory. It prevents treating all 82 snapshots as scored forecasts of the later selected hypothesis.

Valid present outputs include case counts, class distributions, deterministic availability selection, artifact integrity, and explicitly labelled evidence-availability intervals. Those intervals are not market lead times or profitability windows. See the [case inventory](case_inventory.csv) and [machine-readable inventory](case_inventory.json).

## Scoring and implementation findings

The active Batch015 → Batch016 → Batch017 read-only path serves the pinned classified run with Brier null. It does not invoke the generic `evaluate_cases()` scorer. The generic scorer has one direct synthetic three-row metrics test; current regression coverage is much stronger for source pins, availability, classification and fail-closed state than for empirical metric semantics.

| Finding | Evidence class | Bounded next action |
|---|---|---|
| Generic positives include partial realization, wrong timing and wrong beneficiary | Explicit legacy scoring semantics | Freeze a separate exact-target primary metric; retain taxonomy diagnostics |
| `INVALIDATED` contributes to resolved coverage but not the confusion cells | Explicit denominator semantics | State endpoint-specific eligibility and publish every denominator |
| Nullable `target_met` / `horizon_met` lack strict type checks before identity comparisons | Static control-flow defect; no hostile execution in this audit | First reproduce malformed string/integer inputs, then add only the missing boolean-or-null guards |
| `realized_constraint` can reach float conversion without boolean-or-null validation; boolean probability is accepted | Static generic API validation defects; current query does not use this scorer | First reproduce invalid/nonfinite targets and boolean probabilities, then enforce the declared types |
| No direct empirical assertions for Brier, recall, false negatives or censoring | Concrete test-coverage gap | Add focused metric/denominator regression cases under the new protocol |

Static inspection found no malformed nullable mapping fields in the tracked mapping bundles: the current 22 records retain null targets/horizon results and null proposed confidence. No existing corpus corruption or changed historical class is claimed. The code findings require test-first reproduction before a repair can be called validated. This audit does not silently change label mappings or rewrite frozen manifests.

Detailed evidence: [scoring audit](scoring.md) and [test coverage / historical-document precedence](test_coverage.md).

## Frozen evaluation design

[Evaluation protocol V001](protocol.md) and [split inventory](split_inventory.json) assign all 22 examined cases and all their cuts to **DEVELOPMENT_ONLY**. No unseen holdout or prospective cohort has been created. This assignment is an audit record, not a model-training authorization or a runtime policy change.

Future performance evaluation requires a sealed case-selection universe, case/source dependency groups, an exact predictor or rule snapshot, a binary decision or probability, a target, a horizon and an outcome-adjudication policy fixed before the held-out outcomes are inspected. A case and its cuts stay in one group. Shared source/event dependencies must not cross splits. The 21 observed connected components do not establish 21 independent samples; additional dependency edges may merge them.

Primary confusion cells must derive from the frozen decision and independently adjudicated exact-target truth. Partial realization or a wrong-time/wrong-beneficiary result must not be dropped after seeing the outcome to inflate accuracy. When an observable full claim fails its predeclared endpoint, count the failure. Keep genuine censoring and unresolved evidence explicit, with coverage and missingness denominators. Report the existing multi-class taxonomy separately.

Prospective or grouped walk-forward evaluation must freeze cohort membership, source versions, cutoff rules, scoring, benchmarks and exclusions before execution. Earlier folds alone may inform subsequent choices. Negative controls and missed events must come from the declared universe rather than a collection of famous successes. Uncertainty must respect case/dependency groups; the 82 cuts cannot be treated as independent samples. No performance threshold or sample-size gate is invented by this audit.

## Exact remaining evidence

| Packet | Required evidence | Scope |
|---|---|---|
| Frozen prediction / target | Case and version IDs, predictor/rule hash, original timestamp, decision or probability, target and units where applicable, horizon, invalidators, sealing evidence | Required before claiming HYDRA predictive performance |
| Confidence admissibility | Original probability tied to that exact target and cutoff, source/version/hash, provenance and permitted semantics | Required for calibration; not an excuse to invent probabilities from qualitative text |
| Evaluation universe and outcomes | Selection rule, population membership including negatives and nondetections, independent outcome evidence, fixed maturity/contradiction rules, documented missingness | Required for defensible accuracy, recall and false-alarm denominators |
| Historical availability | Exact version/hash, intended cutoff, contemporaneous availability or witness evidence, custody references and a verifiable trust path | Required where stronger exact-source historical availability is claimed |
| Unseen cohort seal | Grouped membership, split policy and hashes sealed before outcome inspection; evaluator and benchmark identities | Required for an honest held-out or forward evaluation claim |

Existing first/second-slice gates are separate from the 22-case policy corpus. Batch018 repository records describe 9/9 raw versions materialized with custody metadata; this audit did not verify those private bytes. Earlier historical cutoffs still need exact-version contemporaneous availability evidence. Batch034 records 30 current versions and 34 active evidence bindings, while historical case 12 remains open. Eaton/GE timestamp literals remain unverified. Older predecessor `REAL_NINE_SOURCE_MATERIALIZATION=NO` output must not override the later repository-recorded custody closure, and that closure must not be promoted into historical availability proof.

The [temporal audit](temporal.md) supplies the exact source inventories, precedence table, scoped blockers and minimum packet fields. Native T5/T6 admission is a separate unresolved authority gate; an evaluation protocol or compatibility PASS cannot grant it.

Trading-return backtesting is outside this completed proof. A future request would additionally need a frozen strategy, point-in-time instrument universe/prices, corporate-action treatment, execution timing, costs/slippage and return/risk benchmarks. None is supplied by the historical classification score or authorized here.

## Disposition

Preserve the current compatibility PASS. Preserve every historical manifest and label. The next executable software work is a bounded test-first reproduction and repair of the typed-input findings, followed by focused evaluator-contract tests. Evidence-dependent scoring remains blocked until the applicable packets and an honest evaluation cohort exist. Additional green regression runs alone cannot supply those missing records.

No canonical mutation, external-action capability, training, trading, admission or readiness promotion results from this audit. Source PR161 and PR162 remain unchanged and unmerged.
