# HYDRA Constraint Runtime

Repository integration of the sealed Constraint V018 runtime/operations stack.

Authority chain:

- V011: site/evidence authority
- V012: runtime traversal/evidence gates
- V013: canonical graph integration
- V014: event normalization/replay
- V015: source adapters + append-only event ledger
- V016: persistence/recovery/golden replay
- V017: polling/raw archive/freshness
- V018: parser drift/failure budgets/deployment guard

Core guarantees:

- no headline-to-ticker shortcut;
- OPEN/C evidence cannot propagate as fact;
- B1/B2 exposure remains candidate;
- future facilities remain temporally gated;
- observed routes are non-exclusive;
- raw responses are archived before parsing;
- cursors advance only after durable ledger append;
- ledger history is append-only and hash-chained;
- stale sources are surfaced as uncertainty, not treated as no-event evidence;
- no automatic trading action is authorized.

Run:

```bash
python -m unittest discover -s constraint-runtime/tests -v
```

The committed canonical graph is a compact runtime projection of the sealed V013 graph. Historical/provenance artifacts remain governed by the existing Constraint evidence lineage.
