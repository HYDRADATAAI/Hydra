# HYDRA backtest evaluation protocol V001

**Status: AUDIT_ONLY_NO_RUNTIME_AUTHORITY.** This is a proposed evaluation contract and static inventory. No backtest, forecast, training, capture, source repair, promotion, or admission was executed or authorized by this document.

Frozen audit input: commit `e4eb1d95c82484a1518dcf037c8d0a99145231bc`, tree `62d4cdfb1f02d8bc31273711c513c765b030de17`, parent main `adaab38e2e2f53c381aa4d2baff38644be92e3d0`. `split_inventory.json` records all 22 cases, all 82 cuts, source associations, exact artifact hashes, observed dependency components, and development-only assignments. Its audit timestamp is not a source-availability timestamp.

## Current evidence and limits

The frozen Batch015 run reports 22 classified cases, 82 replay cuts, 17 `PARTIAL_REALIZATION`, five `UNEVALUABLE`, zero calibrated cases, and a null Brier score. Its digest is `db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1`. These are stored artifact values read statically, not results regenerated in this audit.

**All existing 22 cases and their cuts are development-only because they have been examined. There are zero unseen held-out cases and zero sealed prospective cases.** A new random or temporal partition of these cases cannot restore unseen status. Recovering additional historical evidence could improve provenance or permit a clearly labeled development analysis; it would not create an untouched test set.

| Item | Static finding | Consequence |
|---|---|---|
| Held-out/walk-forward manifests | No relevant manifest found in replay, policy, or Constraint documentation; wider lexical matches were unrelated runtime assertions/environment bootstrap | No out-of-sample performance claim |
| Frozen historical artifacts | Replay input, runner, output and query pins exist; `replay.py` hashes a supplied hypothesis and eligible evidence | Reproducible bytes do not establish a predictor chosen or sealed before outcomes |
| Confidence | All 22 classified rows state no admissible numeric confidence; current mapping audit declares no numeric targets and only one explicit horizon | No calibration score; no invented numeric confidence or retrospective target |
| Target/horizon | CHIPS is the sole mapping row with an explicit horizon; current mapping declarations are dated September 2026 | Retrospective classification rules are not prospective forecast registrations |
| Sampling and benchmarks | No fixed opportunity universe, outcome-independent selection manifest, negative denominator, or benchmark result found | General precision/recall, prevalence and population performance are not established |
| Negative fixture | Paducah fixture explicitly says synthetic, not historical evidence, and do not ingest as a claim | Useful firewall coverage; not an empirical true-negative count |
| First-slice protocol | Existing Batch015–017 protocols explicitly declare `SHADOW_READINESS_PROTOCOL_NOT_ACCEPTANCE_RUN`; acceptance-grade readiness remains NO | Preserve their scope and blockers |

Primary evidence paths are `constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json`, the Batch005 replay-ready and Batch014 classified corpus files, their pinned Batch008–014 outcome/confidence mapping files, `constraint-replay/src/hydra_constraint_replay/{replay,metrics,confidence,outcome_mapping}.py`, and the first-slice evaluation protocols and Batch013 negative-control fixture under `docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/`. The older `EVALUATION_REPORT.md` supplies denominator requirements; its scaffold-era corpus status is not substituted for the newer frozen run.

## Evaluation units and dependence

1. A case is the primary unit. Every cut, revision, hypothesis variant, outcome, and derived record for that case follows one assignment. Eighty-two cuts are not 82 independent cases.
2. Link cases sharing underlying events, policy episodes, exact documents/source versions, derived evidence, or overlapping outcome-generating mechanisms. Take the connected-component closure before allocation. Review aliases and related-event/source families; publisher identity or a common storage bundle alone does not resolve dependence.
3. The inventory finds one exact cross-case document link: Section301 and Section232 share the USITC release URL `https://www.usitc.gov/press_room/news_release/2023/er0315_63679.htm`. Observed links are a lower bound on dependence; the 21 observed components are an upper bound on the number of distinct dependency components because additional links can merge them. They are not 21 proven independent samples. Semantic relationship review is still missing.
4. Every present component remains development-only. A future case linked to an examined case enters a separately labeled dependent continuation cohort, not the primary novel-group holdout. Newly discovered cross-boundary links are reported as contamination; never silently reallocate to improve results.
5. Predeclare one primary forecast origin per case. If repeated-origin forecasting is a separate objective, fix its schedule and within-case weighting before outcomes, preserve all attempts, and calculate uncertainty at the dependency-group level.

## Prospective cohort and walk-forward rule

V001 creates no new split. A future authorized evaluation requires a sealed manifest containing a protocol/version hash; full case/opportunity universe snapshot; grouping rules and group membership; eligibility and exclusion rules; recruitment start/end UTC; forecast origins; exact targets and horizons; outcome sources and maturity lag; immutable predictor/baseline versions; sampling seed and inclusion probabilities; metric/weighting plan; missingness rules; and the intended report schedule.

The manifest and selection algorithm must be fixed before recruitment outcomes are observed and before evaluators inspect the prospective test labels. Commit hashes bind content but do not independently prove when a split or prediction existed; retain verifiable contemporaneous registration/custody evidence. Record enrollment and prediction issuance before their applicable target window begins. An already decided target cannot enter as a future forecast.

For walk-forward fold k, freeze the predictor and baseline at origin `T_k`. Only inputs available at or before `T_k` and training/development labels matured and available before `T_k` are eligible. Predeclare the next recruitment window and horizon-specific maturity date. Close and reveal that cohort on the scheduled report date. A revealed cohort may become development material for a later frozen version, but is consumed as a holdout and cannot be reused as untouched evidence. Group separation and overlapping-window purges remain binding across folds. Purge/embargo duration follows declared target windows and reporting/revision lags, not a convenient arbitrary number of days.

Do not select dates, horizons, thresholds, cohorts, or stopping points after seeing performance. Retain every registered cohort and version, including null and unfavorable results. Any change starts a new version for a later unrevealed cohort; it does not rewrite the old registration.

## Fixed universe, negatives and selection bias

Define the eligible entity/event-opportunity-by-time universe before examining outcomes, independently of HYDRA alarms. Record all eligible units, exclusions with reasons, predictions, abstentions, and observation status. The current hand-curated historical cases do not supply that universe.

If full-universe observation is infeasible, sample controls from that fixed universe with a recorded seed and known inclusion probabilities before outcomes. They become observed negatives only after the registered target window matures with sufficient ascertainment. Do not sample only well-known successes or retrospectively choose confirmed non-events. Distinguish these empirical comparison units from synthetic adversarial fixtures.

Track positive outcomes among non-alarmed units to support a false-negative denominator. Preserve no-alarm and abstention states separately; an abstention is not automatically a negative prediction. Record unobserved, censored, withdrawn, and disputed outcomes; lack of evidence is not evidence of absence. If sampling probabilities differ, report both sample counts and prespecified population-weighted estimates. Without ascertainment/inclusion evidence, report only the bounded observed sample and mark population recall, false-positive rate and prevalence unavailable.

## Frozen predictor and probability contract

Before the prospective window, seal the predictor's code/tree, rule/prompt/model identifier, configuration, retrieval policy, source/version allowlist, decision rule, and output schema. For every opportunity, seal the input cutoff, actual source-version identities, hypothesis, forecast or abstention, and output digest. Deterministic hashes generated after outcomes do not reconstruct a historical prediction. This audit supplies no training or execution authority.

For probability evaluation, define exactly `P(Y=1 by T+H | admissible information at T)` for one specified unit and operational outcome predicate. Fix metric units, direction, target magnitude when relevant, geography/entity scope, horizon, observation procedure, invalidators, and maturity rule. A full conjunction of claims must satisfy the full registered predicate. Formation confidence, a policy objective, an operating quantity, qualitative language, and event probability remain separate types. Never convert current qualitative records or `PARTIAL_REALIZATION` labels into numeric probabilities.

A numeric forecast range needs a predeclared scoring treatment and retained endpoints. The existing midpoint helper is not an independent justification for midpoint scoring. Ordinal mappings require their own contemporaneous frozen mapping evidence. A confusion matrix additionally requires a prediction decision rule or loss-based threshold fixed before outcomes. This audit selects no arbitrary accuracy target or decision threshold.

## Outcomes, primary scoring and maturity

Freeze the binary target and independent adjudication rubric before forecast issuance. Adjudicators should not see forecasts while assigning target truth where separation is practicable. Preserve source/version evidence, observation time, uncertainty, revisions and unresolved disagreements. Freeze the report's label version and report later corrections separately.

The primary confusion matrix derives from the predeclared binary prediction and independently adjudicated target at its fixed horizon. It must not be created by blindly mapping the existing global taxonomy to success/failure. If a complete, observable full target is not met, the corresponding positive full-claim prediction fails. Do not exclude partial realization, wrong timing or wrong beneficiary after observing them to inflate accuracy. Report those taxonomy labels separately as diagnostic explanations. Conversely, an existing case without a defined target/horizon or other scoring prerequisite is declared performance-ineligible before scoring; missing prerequisites cannot be filled from the observed outcome.

Retain open-horizon, censored, disputed and insufficiently observed cases in enrollment/coverage accounting. They are not true negatives. Score only according to the prespecified maturity/ascertainment rule, and publish the excluded/unmatured counts and reasons. Early positive adjudication, if allowed, must be written into the target contract; the scheduled cohort report still includes the complete registered denominator. Preserve revisions and assess missingness sensitivity without relabeling uncertain outcomes to obtain a favorable score.

For eligible future probability forecasts, preregister a proper probability score such as Brier against the same binary target, paired baseline comparison, case/group counts, calibration and coverage. For binary decisions report the four confusion counts and only defined ratios. Keep outcome classification coverage, evidence availability lead time, predictive lead time, software pass rates and forecast accuracy distinct. The stored Batch015 evidence-availability lead is not validated forecasting skill. The existing `metrics.py` positive-label aggregation is not adopted as this strict target-specific primary score.

## Benchmarks and uncertainty

Register benchmarks before test outcomes: an outcome-frequency forecast fitted only to an eligible matured development universe, a persistence forecast where the prior target state is observable and meaningful, and a simple frozen domain rule when applicable. Record failures/inapplicability without replacing a weak benchmark after the fact. The selected 22-case corpus does not establish population frequency. Compare candidate and baseline on identical eligible units, horizons, label versions, and abstention treatment.

Publish raw counts and effect sizes before declaring superiority. Freeze the uncertainty method, confidence level, random seed, resampling unit and fold-combination weights in the prospective manifest. Dependence-aware paired resampling must resample entire case/source-event components, retaining all their cuts; do not treat cuts as independent. If the number/diversity of independent components cannot support the chosen interval, mark the interval insufficient or exploratory and expose the limitation. Report domain/cohort composition, exclusion/missingness rates, and sensitivity to ascertainment and weighting. Keep subgroup and alternate-horizon analyses explicitly exploratory unless registered. No accuracy percentage, sample-size gate or readiness promotion is invented here.

## What blocks progress

| Evidence or design input required | Implementation gap |
|---|---|
| A future genuinely unseen cohort and independently verifiable pre-outcome seals; old cases cannot supply unseen status | Cohort/split manifest and reveal/consumption enforcement |
| An outcome-independent eligible universe, selection probabilities and sufficient outcome ascertainment | Universe, enrollment, exclusion, abstention and missingness ledgers |
| Defensible targets/horizons and admissible probabilities or prospective frozen forecasts | Typed target/maturity contract and frozen predictor/decision manifests |
| Source-version availability evidence and curated event/source-family relationships | Dependency closure, provenance cutoff checks and cross-fold contamination guard |
| Eligible matured reference data and prespecified reporting choices | Frozen baselines, strict target scorer, paired comparison and clustered uncertainty reports |

These gaps are not repaired by a larger replay count, greener CI, relabeling current outcomes, or selecting a favorable historical split. The existing authority/evidence blockers retain their states. V001's result is **BACKTEST_READINESS=BLOCKED_FOR_UNSEEN_PERFORMANCE_CLAIMS** with a concrete prospective protocol proposal and an honest development inventory; canonical mutation, external actions, model training, trading and admission/readiness promotion remain unauthorized.
