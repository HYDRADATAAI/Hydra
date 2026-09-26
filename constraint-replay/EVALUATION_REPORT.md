# Historical Replay Evaluation Report

## Status

Framework: IMPLEMENTED FOUNDATION  
Real historical gold corpus: NOT YET POPULATED  
Historical performance claims: NOT YET ADMISSIBLE

## Controls implemented

- Fail closed when evidence KNOWN_AT is later than REPLAY_T.
- Require timezone-aware replay/evidence/outcome timestamps.
- Require provenance URI and source hash.
- Freeze evidence identity, temporal metadata, source hash, and payload hash into the prediction hash.
- Reject outcome impact timestamps at or before replay time.
- Keep outcome/subsequent evidence outside the historical evidence boundary.
- Distinguish unresolved/unevaluable cases from resolved scoring denominators.

## Evaluation metrics

Precision, recall where observable, false-positive rate/count, false-negative count, mean/median lead time, Brier score, historical coverage, provenance completeness, and leakage violation count.

## Current interpretation

No historical accuracy number is reported because the repository does not yet contain a provenance-complete gold corpus. Reporting one would manufacture evidence. The next gate is to ingest sourced cases from the geography/resource/infrastructure/policy layers and evaluate multiple replay cuts per case.

## Acceptance gate for serious Constraint run

1. At least 20 provenance-complete cases across multiple mechanisms.
2. Multiple PIT cuts for cases where evidence evolved materially.
3. Zero admitted lookahead violations.
4. All scored evidence has stable source identity/hash and KNOWN_AT.
5. False-negative denominator documented rather than inferred from detected cases alone.
6. Calibration and lead-time distributions reported with sample counts.
7. Corpus and evaluator run reproducibly in CI.
