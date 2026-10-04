# Static corpus findings

Frozen commit `e4eb1d95c82484a1518dcf037c8d0a99145231bc`, tree `62d4cdfb1f02d8bc31273711c513c765b030de17`, main `adaab38e2e2f53c381aa4d2baff38644be92e3d0`.

The governed corpus supports a bounded retrospective descriptive replay. It does not currently support a HYDRA prediction-accuracy or probability-calibration claim. The inventory reconciles exactly 22 selected case families and 82 cutoffs: 17 labels are PARTIAL_REALIZATION and five are UNEVALUABLE. Those 82 cutoffs are repeated within-case states, not 82 independent predictions.

The 22 historical hypotheses are cited public statements, operational commitments, objectives, or risk narratives. No immutable HYDRA model prediction, model/run version, cutoff-bound input snapshot, or contemporaneous prediction receipt is supplied by the inspected case artifacts. Published narrative hypotheses must not be relabeled as HYDRA predictions.

Every case has NO_PRECOMMITTED_CONFIDENCE_SOURCE and NO_SOURCE_GROUNDED_CONFIDENCE_VALUE in the governed Batch015 run. Historical confidence-source lists are empty, proposed numeric confidence is null, and all ordinal-mapping lists are empty. The confidence semantic counts are: TARGET_OR_OBJECTIVE=2, QUALITATIVE_RISK=5, QUALITATIVE_EXPECTATION=14, OPERATIONAL_COMMITMENT=1.

All 22 outcome mappings explicitly lack a numeric success target. Only the CHIPS case defines a horizon; its ten-year window is still incomplete in the admitted evidence. Three UNEVALUABLE cases retain open contradictions and two retain incomplete outcome windows. All mapping declarations are dated September 26, 2026, after the first admitted outcome observations. These are retrospective labels, not precommitted scoring targets.

Only 1 classified hypothesis anchors exactly coincide with an original Batch005 cutoff. 39 cutoffs precede the hypothesis's declared availability; 6 cutoffs are on/after the first classified outcome's declared availability. These two groups are disjoint, leaving 37 metadata-timing-compatible cuts, all still ineligible for prediction-performance claims. This does not assert that the existing replay leaks: each cutoff has its own permitted event inventory. These are annotated individually. The classification anchor and the 82 descriptive cutoffs must not be treated as interchangeable forecast timestamps.

Source publication/availability timestamps are preserved exactly as recorded. The source evidence digests hash normalized narrative text, not captured original source bytes. File Git blobs and SHA-256 establish the inspected repository version, not independent historical availability, custody, or timestamp authority.

Static pin join: {'EXACT_CURRENT_BLOB': 146, 'EXACT_DECLARED_CI_SUCCESSOR': 1}. The exact Batch015 CI successor is represented explicitly, with the historical manifest preserved. 86 normalized-evidence checks match. 58 artifact identities include exact Git blob, SHA-256, and byte length. These are static checks, not a new runtime-validation claim.

Case dependencies are recorded through exact source-pair membership, event types, physical references, shared source URLs and publishers. Shared documents and policy/commodity contexts prevent assuming that all cases are independent observations. Related-case links are dependency indicators and are not causal estimates.

| Case | Cuts | Label | Confidence semantics | Case-specific outcome limitation |
|---|---:|---|---|---|
| bis-semiconductor-controls-2022 | 4 | PARTIAL_REALIZATION | TARGET_OR_OBJECTIVE | No numeric success target; attribution/threshold limits remain |
| black-sea-grain-corridor-2022 | 4 | PARTIAL_REALIZATION | QUALITATIVE_RISK | No numeric success target; attribution/threshold limits remain |
| china-gallium-germanium-controls-2023 | 3 | PARTIAL_REALIZATION | QUALITATIVE_RISK | No numeric success target; attribution/threshold limits remain |
| eastern-mediterranean-offshore-drilling-dispute-2019-2020 | 4 | UNEVALUABLE | QUALITATIVE_RISK | Open contradiction |
| eu-battery-ipcei-state-aid-2019 | 2 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| eu-cbam-transitional-phase-2023 | 3 | UNEVALUABLE | QUALITATIVE_EXPECTATION | Incomplete outcome window |
| eu-fifth-package-coal-and-port-restrictions-2022 | 2 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| eu-russian-oil-import-restrictions-2022 | 4 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| germany-uniper-nationalization-2022 | 3 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| germany-wilhelmshaven-lng-commissioning-2022-2023 | 5 | PARTIAL_REALIZATION | OPERATIONAL_COMMITMENT | No numeric success target; attribution/threshold limits remain |
| imo-sulphur-2020-regulation | 3 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| japan-korea-export-control-relations-2019 | 4 | UNEVALUABLE | QUALITATIVE_RISK | Open contradiction |
| nord-stream-2-certification-state-2021-2022 | 3 | PARTIAL_REALIZATION | TARGET_OR_OBJECTIVE | No numeric success target; attribution/threshold limits remain |
| panama-canal-drought-transit-policy-2023 | 5 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| russia-food-import-embargo-2014 | 2 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| suez-ever-given-2021 | 6 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| us-china-section301-multi-stage-trade-dispute-2018 | 7 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| us-chips-act-2022 | 4 | UNEVALUABLE | QUALITATIVE_EXPECTATION | Incomplete outcome window |
| us-pdvsa-sanctions-2019 | 2 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| us-section232-steel-tariff-2018 | 3 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| us-section45x-advanced-manufacturing-incentive-2022 | 5 | PARTIAL_REALIZATION | QUALITATIVE_EXPECTATION | No numeric success target; attribution/threshold limits remain |
| wto-china-rare-earths-resource-dispute-2014-2015 | 4 | UNEVALUABLE | QUALITATIVE_RISK | Open contradiction |

The JSON preserves every cutoff record, hypothesis/outcome source and timestamp, confidence statement and semantics, quantitative/qualitative outcome record, original mapping rationale, eligibility blocker, family dependency and governed pin relation. The CSV has one row per case and JSON-encoded detail cells. No HYDRA runtime, model training, external acquisition, source edits or authority promotion occurred.

Primary governed inputs:

- `constraint-replay/corpus/HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH014_20260926.jsonl` — Git blob `a5f09df390f00c4873a5f2b4b839f9b69a54888d`; SHA-256 `e759f9a26d6e71f45779e5a8f31bb9636f4949d534f4b39461015074a89c798c`.
- `constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl` — Git blob `341936053470046548be540e25f35e26b4aac5b7`; SHA-256 `c0dbf2a94290e50224a503a2c69d7218f62877885c0d83fc86ce30b95c6ea1de`.
- `constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH014_20260926.json` — Git blob `f1e9449dc2ca043cd0f3405038d7571f9fa2dbf3`; SHA-256 `87350058d2c25781bd6a73af55658d0a977626d21f267bc3151f1e38b3d05405`.
- `constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json` — Git blob `67fc5fb5883fb4ca510eee5a8c908c298d1b5bc9`; SHA-256 `b67ec91bcf2065e06ee8be766e1934a1758e4b8bbc1ff9c2e29b35869ba4a5c8`.
- `constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json` — Git blob `7d2deb998e8c3362cea861f48909b78c1c00a42d`; SHA-256 `2c3414eaff4ce90d1ba0a374a931765cf209f01380afcad6edeefbe45be6a4bc`.
- `constraint-replay/runtime/HYDRA_CONSTRAINT_BATCH017_MULTIDOMAIN_READONLY_MANIFEST_20260926.json` — Git blob `fc42afc6bf5af5ea65d8cb65ef79837cf0e55c94`; SHA-256 `e3908f353b74e0ae1f4d093630ff14276f7cec76d56be6b1d04f43ea98bfd239`.
- `constraint-replay/runtime/HYDRA_CONSTRAINT_BATCH015_CI_CONTRACT_SUCCESSOR_V001_20261003.json` — Git blob `382aca39cd89c89657becb45b726870a3f687aea`; SHA-256 `c1c1f6027de9312680c31662ed2c1bff2170403598da5697607e5035b1908c90`.

Static shape reconciliation: mapping booleans retain actual JSON booleans; target_met and horizon_met are null for all 22 cases, including the explicit unfinished CHIPS horizon. proposed_confidence_at_t is null and historical_confidence_source_ids is empty for every case. Policy physical relations contain confidence weights, preserved as relation metadata and not interpreted as calibrated prediction probabilities. CSV readback reconciles 22 unique cases and all 82 cutoff records.
