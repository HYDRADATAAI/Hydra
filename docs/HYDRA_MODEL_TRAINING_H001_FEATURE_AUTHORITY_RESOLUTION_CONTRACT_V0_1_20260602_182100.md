# HYDRA H001 Feature Authority Resolution Contract v0.1

## Decision
- overall_status: `PASS`
- final_status: `MODEL_TRAINING_H001_FEATURE_AUTHORITY_RESOLUTION_CONTRACT_PASS_PARKED`
- resolution_status: `H001_FEATURE_AUTHORITY_RESOLUTION_CONTRACT_COMPLETE_READY_FOR_REVIEW`
- resolution_decision: `ACCEPT_FEATURE_AUTHORITY_RESOLUTION_FOR_OUTPUT_REVIEW_NO_SCHEMA_MUTATION`
- quality_classification: `H001_FEATURE_AUTHORITY_RESOLUTION_SELECTED_ARTIFACT_CONFIRMED_SOURCE_AUTHORITY_UNRESOLVED_NO_SCHEMA_MUTATION`
- recommended_next_gate: `MODEL_TRAINING_H001_FEATURE_AUTHORITY_RESOLUTION_OUTPUT_REVIEW_CONTRACT_v0.1_AFTER_FEATURE_AUTHORITY_RESOLUTION_CONTRACT`

## Interpretation
Feature authority resolution confirmed the selected 45-feature dryrun artifact is internally consistent and appears tied to generated FEATURES_USED artifacts, but no bounded upstream authority artifact reconstructed the locked 60-feature source reference hash. Treat the governing feature authority as unresolved. Do not mutate schema, promote, or open another model lane until a later authority-source decision names the governing feature source.

## Feature Authority Evidence
- source_feature_count_used: `60`
- selected_feature_count: `45`
- feature_count_delta_vs_source: `-15`
- source_reference_feature_list_reconstructed: `False`
- selected_feature_artifact_reconciled: `True`
- governing_feature_authority_classification: `SELECTED_45_FEATURES_USED_ARTIFACT_CONFIRMED_SOURCE_60_AUTHORITY_UNRESOLVED`

## Guardrails
Resolution contract read only prior selector/checkpoint artifacts, bounded authority artifacts, and dataset headers. It did not read dataset values, train, score, compute model metrics, read test data, write model artifacts, write row-level predictions, simulate/backtest, generate trade signals, mutate Hydra state, promote current-best, remove quarantine, reopen branches, mutate dataset/splits, mutate schema, or reopen an identical named-lane loop.
