# HYDRA Constraint Runtime

Repository integration of the sealed Constraint V018 runtime/operations stack.

Thread E holds this integration at **runtime candidate only**. A1/A2 labels
permit candidate traversal; they cannot produce admitted `CONFIRMED` exposures.
Replay, traversal, canary, deployment and operations reports carry an explicit
`admission.status=BLOCKED`, `canonical_admission=false` and
`readiness_promotion=false`. No configuration or claimed PASS value unlocks it.
Enabled deployment sources must be explicit read-only canaries.

`CanonicalEvent` and ledger CREATE/MERGE records refer to normalized event
identity, not accepted canonical evidence. Existing stored labels, dates,
normalization notes and hash chains are preserved. Date fallback, source rank,
lineage presence, recovery PASS and current canary success do not establish
authority or historical availability. Operational PASS is explicitly scoped.

The hold retains D_OWNER_GATE=BLOCKED, IMPLEMENTATION_ADMITTED=NO, PIT-002B
open, Eaton and GE Vernova TIMESTAMP_UNVERIFIED, trusted timestamp verification
NOT_IMPLEMENTED, and the full temporal/authority audit NOT_RUN. Authorized
real-outcome evidence is not established by this runtime. This conservative hold
does not implement receipt/signature verification or a positive admission path;
lifting it requires separately governed authority integration and evidence.

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
- polling honors each source's `max_rps` across request attempts; complete poll transactions are serialized within one `PollRunner` to protect shared ledger/cursor state, and limits are not shared across runner instances or processes;
- retry delays honor numeric and HTTP-date `Retry-After` values up to `cap_seconds`; malformed values use exponential backoff;
- cursors advance only after durable ledger append;
- ledger history is append-only and hash-chained;
- stale sources are surfaced as uncertainty, not treated as no-event evidence;
- no automatic trading action is authorized.

Run:

```bash
python -m unittest discover -s constraint-runtime/tests -v
```

The committed canonical graph is a compact runtime projection of the sealed V013 graph. Historical/provenance artifacts remain governed by the existing Constraint evidence lineage.
