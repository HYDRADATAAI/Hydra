# Asana Payload — Hydra Daily Planner Review Gate v0.1
## Subtask 5 — Retest Quality Warnings

### Purpose

Define how Hydra must warn when a retest is weak, degraded, over-tapped, or not suitable to trust without stronger confirmation.

This section answers:

“When is a retest not clean enough to trust?”

### Required Output Format

```text
Date reviewed:
Instrument(s):
Source(s):
Retest warning source:
Primary retest quality risk:
Weak retest conditions:
Strong retest conditions:
Level hold requirement:
Reclaim/reject requirement:
First touch vs later touch note:
Compression/expansion context:
No-trade retest conditions:
Retest confidence:
What Hydra is allowed to infer:
What Hydra is NOT allowed to infer yet:
```

### Done Means

This section is complete only when retest-quality warnings are reviewable as planner context without creating trade signals or measuring outcomes.

A completed Retest Quality Warnings section must:

1. Identify the reviewed date and instrument(s).
2. Identify the source of retest-quality warnings.
3. Distinguish weak retest conditions from stronger retest conditions.
4. Define what level hold, reclaim, or rejection behavior must be reviewed.
5. Note first-touch vs later-touch quality issues.
6. Include compression/expansion context when available.
7. Define no-trade retest conditions as context, not as execution logic.
8. Assign confidence.
9. Avoid level-distance calculations.
10. Avoid price-reaction measurement.
11. Avoid MFE/MAE or outcome hindsight.
12. Avoid trade signal generation.
13. Avoid planner/market join logic.

### Explicitly Blocked In This Subtask

1. no market-data scan
2. no recursive scan
3. no multi-file scan
4. no planner/market join
5. no level-distance calculation
6. no price-reaction measurement
7. no MFE/MAE calculation
8. no outcome measurement
9. no trade signals
10. no queue mutation
11. no ML labels
12. no simulation
13. no execution
14. no external API calls
15. no Asana mutation
