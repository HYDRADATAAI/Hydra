# Bounded static scoring audit

Frozen head `e4eb1d95c82484a1518dcf037c8d0a99145231bc`, tree `62d4cdfb1f02d8bc31273711c513c765b030de17`, main `adaab38e2e2f53c381aa4d2baff38644be92e3d0`. Static source/data reads only: no HYDRA imports, runtime, tests, network acquisition, source edits or remote mutations. Defect proofs below are static, not executed reproductions.

**The current Batch015→016→017 query path does not invoke the generic evaluator.** It provides frozen, uncalibrated classification reporting. Its 22 cases comprise 17 `PARTIAL_REALIZATION` and 5 `UNEVALUABLE`; all lack a numeric confidence field and remain uncalibrated. Brier is explicitly null. Neither 17/22 nor classification coverage 1.0 is predictive accuracy. [RUN:2–9,365–410]

## Actual path

- Batch015 CLI imports and calls `run_classified_replay_e2e`. That function loads replay-ready, classified-gold and promotion records, validates artifact pins and uncalibrated eligibility, and produces class counts and descriptive evidence-availability leads. It never calls `evaluate_cases` or `replay_case`. [S15:8–30; E:10–12,56–115,157–197]
- Batch016 CLI constructs `ConstraintReplayQueryService`. The constructor reads the frozen run and execution manifest, validates pinned bytes, aggregate invariants and blocked calibration. `summary()` copies stored sections. [S16:50–67; Q:108–136,142–263,285–295]
- Batch017 constructs that Batch016 service, joins policy/physical records, then nests its stored replay summary. Its integrity response leaves T6 dormant. [S17:41–57; X:10,82–118,342–382]
- Package `__init__` imports/exports the generic function; that does not invoke it. Repository Python reference search finds its only invocation in `test_replay.py`. [I:1–4,72–73; T:48–54]

The 82 cuts are replay-ready inventory. Batch015 iterates case IDs and emits one classification row per case; it does not score 82 independent forecasts. [E:93–130,157–166]

## Generic evaluator definitions

All supplied cases first pass through `replay_case`; one rejected case aborts the entire aggregation. Let `R` be the eight resolved labels below. [M:4–9]

| Label | Confusion cell | In resolved coverage | Eligible for Brier/lead |
|---|---|---|---|
| TRUE_POSITIVE | TP | Yes | Yes, if required field present |
| PARTIAL_REALIZATION | TP, full credit | Yes | Yes, if required field present |
| RIGHT_MECHANISM_WRONG_TIMING | TP, full credit | Yes | Yes, if required field present |
| RIGHT_CONSTRAINT_WRONG_BENEFICIARY | TP, full credit | Yes | Yes, if required field present |
| FALSE_POSITIVE | FP | Yes | Yes, if required field present |
| TRUE_NEGATIVE | TN | Yes | Yes, if required field present |
| FALSE_NEGATIVE | FN | Yes | Yes, if required field present |
| INVALIDATED | None | Yes | Yes, if required field present |
| UNRESOLVED | None | No | No |
| UNEVALUABLE | None | No | No |

[M:4–22] `realized_constraint` does not determine a confusion cell; the caller-supplied label does. No threshold is applied to confidence and no target, direction, horizon or beneficiary adjudication occurs.

- **Precision:** TP/(TP+FP), null for zero denominator. INVALIDATED contributes to neither term. [M:10–14]
- **Recall where observable:** TP/(TP+FN), null for zero denominator. There is no opportunity census, missed-event discovery or validation of `false_negative_evidence`; this cannot establish population recall. [M:10–15; D:35–42]
- **False-positive rate:** FP/(FP+TN), null for zero denominator. This is distinct from 1−precision. [M:11–16]
- **Resolved count / historical coverage:** `len(R)` and `len(R)/len(all supplied cases)`; null coverage for an empty batch. UNRESOLVED/UNEVALUABLE remain in the all-case denominator. This measures label-resolution fraction within submitted cases, not representative historical coverage. [M:4–9,24–26]
- **Brier:** mean `(confidence_at_t − float(realized_constraint))²` across `R` with non-null realized target. INVALIDATED can contribute; unresolved/unevaluable cannot even if they carry a realized boolean. There is no confidence-source gate, label/target consistency check, or horizon-specific target derivation. Null when empty; its denominator is not reported. [M:18–22,34; D:22–42]
- **Mean/median lead:** `(impact_first_observed_at − replay_t)/86400` across `R` with an impact timestamp, including any qualifying FP/TN/FN/INVALIDATED. No `expected_horizon_days` check is applied. Null when empty. [M:17,32–33; R:57–62]
- **Provenance completeness and leakage count:** every successfully returned row carries `True` and `[]`; a successful nonempty aggregate therefore reports completeness 1 and leakage count 0. Detected violations raise before a report exists. These are accepted-input diagnostics, not observed rates over rejected inputs or independently verified historical evidence. [M:8,35–36; R:24–49,69–71]
- **Weighting:** one equal contribution per supplied row; no case-ID deduplication, family weighting or repeated-cut adjustment. [M:7–9,24]

## Proven defects versus semantics and gaps

**SCORING-DEFECT-001 — unvalidated binary Brier target.** `Outcome.realized_constraint` is annotated bool/null and its schema requires boolean/null. The dataclass imposes no runtime validation; `replay_case` never checks this field, and the evaluator converts any non-null value with `float()`. Direct API input `realized_constraint=2` therefore reaches y=2; numeric NaN reaches a nonfinite result. This is a statically proven validation defect, not evidence that current frozen records contain malformed values. [D:35–42; SO:7–10; R:17–22,63–71; M:19–22]

Proposed bounded future repair: require exact bool or null at the generic boundary, then validate finite scoring inputs. Test this before changing runtime. An arithmetic illustration only, not performance or an executed test: p=0.8 and malformed y=2 yields 1.44, outside the binary Brier range.

**SCORING-DEFECT-002 — boolean confidence admitted as numeric.** The only check is `0 <= confidence_at_t <= 1`; Python bool satisfies it. `True` can therefore silently act as probability 1, despite the numeric JSON schema excluding booleans. Numeric NaN/infinite confidence are already rejected by this range check and are not defects claimed here. [D:22–28; SR:7–12; R:17–20]

Proposed bounded future repair: reject bool/non-numeric values and require finite numeric p within [0,1] in the generic API, with targeted hostile tests. These two findings concern the generic direct API; they are distinct from nullable mapping-input boolean validation audited by the owners lane.

**Explicit legacy semantics, not demonstrated arithmetic bugs:** full positive credit for partial/wrong-timing/wrong-beneficiary is written directly into the positive set. INVALIDATED is explicitly resolved but absent from TP/FP/TN/FN, while it may enter Brier/lead. The outcome mapper distinguishes full target proof, timing failure and inconsistent direction, so generic metrics must not be presented as exact-target forecast accuracy. No frozen binary specification was found resolving INVALIDATED's denominator treatment. Preserve historical behavior; introduce a versioned future contract instead of silently relabeling. [M:4–22; O:98–123]

**Evidence gap:** generic hypotheses hold numeric confidence without a confidence-source binding; outcomes do not require source IDs. The generic gate checks asserted timestamps and nonempty provenance strings, not trusted historical availability. An empty evidence list traverses no evidence checks and receives `provenance_complete=True`. Content hashing is not proof of historical precommitment. The richer promotion checks are separate and are not invoked by the generic evaluator. [D:11–42; R:24–56,69–71; P:89–109]

**Cohort gap:** current classified cases provide neither calibrated forecasts nor a scored negative/missed-positive universe. Inventing confidence or relabeling the 22 cases cannot establish recall, false-positive rate or Brier. `gold_cases.jsonl` remains explicitly scaffold-only. [RUN:2–9,365–410; G:1–3]

**Lead semantics:** Batch015 includes all 22 case leads, including five UNEVALUABLE cases, measured to outcome evidence observation. This is evidence-availability timing, not validated predictive warning lead, tradable reaction time or event-onset time. It also differs from the generic resolved-only lead cohort. [E:112–125,173–179; RUN:348–362,396–403]

**Test gap:** `test_metrics` covers TP/FP/TN and asserts count, FP count, precision, FPR and median. It does not assert recall, FN, Brier, partial/timing/beneficiary mapping, INVALIDATED, zero denominators, null realized targets, malformed numeric types or duplicate-unit handling. Existing replay tests do inspect future evidence, provenance, timestamp and hash behavior. Tests were read, not executed in this audit. [T:13–54]

Hypothetical arithmetic illustration, not corpus performance: positive alerts labeled TP, wrong-timing and INVALIDATED yield legacy precision 1 (two broad positives and no FP). If a preregistered exact in-horizon target was met only by the first, and the other two are completely observed failures, strict precision would be 1/3. Do not retrofit this illustration onto the historical 22 cases.

## Proposed frozen scoring definitions

`PROPOSED_CONSTRAINT_SCORING_V1` is a proposal, not approved policy or an activated evaluator.

1. **Freeze the unit and population.** One preregistered `(event_family_id, endpoint_id, entity_id, replay_t, horizon_end)` unit. Choose one primary cutoff per family before outcomes; additional cuts are sensitivity analyses, not independent samples. Reject duplicate unit IDs. Freeze inclusion rules and an opportunity census or explicit sampling scheme, including missed positives and negative opportunities; retain all enrolled units and exclusion reasons.
2. **Freeze the exact event.** Define mechanism, direction, threshold if applicable, geography/entity or beneficiary, and finite horizon. Set y=1 only when independent evidence supports that event within the window; y=0 only when a complete reliable window establishes nonoccurrence. Incomplete, pending, contradictory or unsupported truth remains UNKNOWN, never automatically negative or half credit.
3. **Freeze the prediction.** Define p as the probability of that exact event by its horizon, based only on admissible pre-cutoff evidence. Require source/version/time binding for p. Derive threshold tau from the declared decision objective and loss/cost specification, document that rationale, and fix/seal it before accessing unseen evaluation outcomes; d=1 iff p≥tau. There is no default threshold and no tuning against evaluation outcomes. Categorical-only evaluation requires independently frozen d and cannot supply Brier.
4. **Use a disjoint confusion matrix.** For fully observed units with frozen d: TP=(d=1,y=1), FP=(d=1,y=0), TN=(d=0,y=0), FN=(d=0,y=1). Counts partition the evaluated cohort. Descriptive labels do not select cells by themselves. Precision=TP/(TP+FP); recall=TP/(TP+FN); FPR=FP/(FP+TN). Zero denominators return null plus a reason. Population recall requires the declared opportunity universe; otherwise label it conditional cohort recall.
5. **Score all eligible numeric forecasts.** Brier is mean `(p−y)²` over every fully observed, protocol-eligible numeric-probability unit, including adverse outcomes and both positive/negative predictions. Do not select based on successful labels. Require finite numeric p, exact bool y, and report Brier N plus excluded counts. No admissible historical p means null with `NO_ADMISSIBLE_NUMERIC_CONFIDENCE`. Brier measures probability error; it alone does not demonstrate calibration.

| Descriptive label | Primary future treatment |
|---|---|
| TP/FP/TN/FN | Require consistency with frozen d and adjudicated y; reject contradictions. |
| PARTIAL_REALIZATION | Adjudicate the exact endpoint. Complete full-claim failure can be y=0; genuinely unobservable truth is UNKNOWN. Do not blanket-exclude or auto-credit. |
| RIGHT_MECHANISM_WRONG_TIMING | y=0 for the frozen in-horizon event once its window is completely observed; later realization is secondary description. Never extend the horizon retrospectively. |
| RIGHT_CONSTRAINT_WRONG_BENEFICIARY | For the frozen beneficiary endpoint, evidenced failure is y=0. A separately frozen mechanism endpoint may be y=1. Do not switch targets after outcomes. |
| INVALIDATED | Complete event falsification is y=0. Data-integrity invalidation is protocol-invalid and remains in enrollment/exclusion counts; it cannot silently disappear to improve scores. |
| UNRESOLVED/UNEVALUABLE | UNKNOWN until supported; exclude from point-valued metrics with exact reason/count. Do not assume existing labels alone prove the future target's truth. |

Publish enrolled, pre-cutoff-eligible, observed, numeric-probability, categorical-only, pending, invalid, abstained and excluded counts; TP/FP/TN/FN and every metric denominator; Brier N and lead N. Separate eligibility/enrolled, observed/enrolled and scored/enrolled coverage. Preserve descriptive labels and endpoint strata.

For a future successful-event lead metric, use only observed positives for the exact endpoint and report time from frozen prediction to first valid observation, explicitly distinguishing occurrence/publication/acquisition timestamps. Keep the historical all-case Batch015 evidence-availability summary unchanged.

Freeze protocol/cohort/holdout hashes, endpoint, horizon, threshold, exclusion policy, weights and adjudication rules before evaluation. Separate event families across held-out splits and guard against later-version/outcome leakage. A hash does not authenticate its historical signing time. This proposal grants no model training, trading, canonical mutation, capture or admission/readiness promotion. No past labels or manifests are rewritten.

Probability scoring and calibration remain **BLOCKED** by missing admissible probabilities for a frozen target. Binary decision accuracy is separately **BLOCKED** by missing frozen decisions, target/cohort definitions and independent adjudication; it does not require numeric confidence. The immediate authorized deliverable is this static report and proposed definitions.

## Immutable references

Reference syntax `M:4–16` means the listed file and line numbers at the frozen head. Exact Git blob bindings follow.

| ID | Repository path | Git blob SHA |
|---|---|---|
| M | `constraint-replay/src/hydra_constraint_replay/metrics.py` | `0516d5ff149369bf185ef9deb71e19caf07d24e2` |
| R | `constraint-replay/src/hydra_constraint_replay/replay.py` | `4e73623ce36be46c5250ac6f19b229a6d3255bb2` |
| D | `constraint-replay/src/hydra_constraint_replay/models.py` | `cdba818e6c876d8a6dd32278e83a57ec913ee663` |
| T | `constraint-replay/tests/test_replay.py` | `1581f60eb5a53a94cfe0746eecc568e4397f8df0` |
| E | `constraint-replay/src/hydra_constraint_replay/end_to_end.py` | `bb55c04e2761edb44ae66d1c00e18171d8e5938e` |
| Q | `constraint-replay/src/hydra_constraint_replay/query.py` | `eb5f5983ad73ac4dc904f117ed764d7ebad7b7c0` |
| X | `constraint-replay/src/hydra_constraint_replay/multidomain.py` | `efe6eaa29119852f0c429d49f7de937e6d98e71f` |
| C | `constraint-replay/src/hydra_constraint_replay/classified_gold.py` | `1064d30bc29ea6a0239df7ed26eb96fcc385a8aa` |
| P | `constraint-replay/src/hydra_constraint_replay/promotion.py` | `e89ff5aac1662f081f982657f8cc7d5a90d53a5a` |
| O | `constraint-replay/src/hydra_constraint_replay/outcome_mapping.py` | `bd5ca147ece8c1f6952c93ea775f1833054d801d` |
| SR | `constraint-replay/contracts/replay_case.schema.json` | `2d258850ff81340f7fd651a72a57315815d683b0` |
| SO | `constraint-replay/contracts/outcome.schema.json` | `0ac3e56d2786933e30591cbd2ea912ad769bccaf` |
| RUN | `constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json` | `67fc5fb5883fb4ca510eee5a8c908c298d1b5bc9` |
| TE | `constraint-replay/tests/test_end_to_end_batch15.py` | `44b6fabf1e73c2183017b49f185a579e40f08038` |
| TQ | `constraint-replay/tests/test_query_batch16.py` | `7fb4c0debbebbd8eb71c155f5510429fc682a8f9` |
| I | `constraint-replay/src/hydra_constraint_replay/__init__.py` | `993b3346c26bd3eaee22229fbff9e53c724937d3` |
| S15 | `constraint-replay/scripts/run_HYDRA_CONSTRAINT_BATCH015_classified_replay_e2e_20260926.py` | `8d3fb97b17aea487083203a4900e1225c98505c8` |
| S16 | `constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py` | `8915031755743f643981ff8e13eb27af46e98ec7` |
| S17 | `constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py` | `66a81ba9d5e663277396235b0032cf05b6464684` |
| G | `constraint-replay/corpus/gold_cases.jsonl` | `1e8643478af1cf0f1ee3bc162d094d6e2b61ed23` |
