Combined PR119 / PR138 / merged PR141 validation

This branch is a validation-only carrier. Do not merge this PR or its harness into main.
The source candidate is pinned separately at dee8c3fa4cd2e49bd3573f62715c5fe4e2108d0d,
tree 9ca099c72f1a440d77119eecc651fd6392dc0ce3 (737 source files).
Ordered parents are current main a738e851183ed4a21e32bac30a5d0a60762e7193,
PR119 head 417174daa31761ad9eaeba56ca6306b3050ada7a,
and PR138 head 8d570da75b594ceca062ba1a53fb6164f6dce3e2.
PR141 is already merged through current main.

The Windows workflow checks out the pinned source into D:\NYX_PORTABLE,
keeps the validation harness outside that source checkout, and validates exact
Git identities, reproducible construction, changed-path ownership, source hashes,
15 test groups, and Windows path/worktree/symlink behavior. The three synthetic
canary aggregation probes do not issue network requests.

The original C/D harness is bound to repository commit
b37f01bc3368ac7833b9a2d60f03e3ff8266c778. Adaptations preserve its complete
inventory, add PR141/PR138 coverage, and update one historical hostile assertion
to PR141's reviewed explicit rejection semantics. No test case is removed.

Passing validation does not grant implementation admission, owner authority,
historical availability, timestamp verification, canonical promotion or production approval.
PIT-002B remains open; Eaton/GE remain TIMESTAMP_UNVERIFIED;
D_OWNER_GATE remains BLOCKED and IMPLEMENTATION_ADMITTED remains NO.
