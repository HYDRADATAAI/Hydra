# Asana Payload — Hydra Daily Planner Review Gate v0.1
## Subtask 7 — Invalidations

### Purpose
Define what proves a market context, bias, scenario, key level, or confirmation read wrong before Hydra is allowed to treat the review as complete.

This section answers:

“What would invalidate the plan?”

### Required Output Format

```text
Date reviewed:
Instrument(s):
Source(s):
Invalidation source:
Primary invalidation condition:
Bullish invalidation:
Bearish invalidation:
Range/rotation invalidation:
Level invalidation:
Scenario invalidation:
Confirmation-failure invalidation:
Conflicts / unknowns:
Invalidation confidence:
What Hydra is allowed to infer:
What Hydra is NOT allowed to infer yet:
```

### Done Means
This section is complete only when invalidation logic is reviewable as planner context without creating trade signals, measuring outcomes, or joining market data.

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
