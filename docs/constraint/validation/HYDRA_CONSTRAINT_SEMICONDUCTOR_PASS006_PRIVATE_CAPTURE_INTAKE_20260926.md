# HYDRA Constraint semiconductor Pass006 — private capture intake

Provides an executable bridge from the six Batch018 and four Pass004 source registry entries to existing T1 private raw-artifact receipts. It neither downloads documents nor creates source-version identities. No source bodies or receipts are published with this change.

## Execution

1. Run `python tools/hydra_constraint_semiconductor_pass006_capture_intake.py --list-sources` to enumerate the ten exact source IDs, locators and conservative availability floors.
2. Capture and review the source documents through the existing authorized acquisition path. Persist them outside the public repository using `hydra_constraint_t1_raw.cli`, with owner-assigned source-version IDs, the exact registered URL as source locator, actual acquisition/availability timestamps and reviewed disposition. A locator alone does not prove document authenticity; that remains an acquisition/review responsibility.
3. In private storage, create a JSON object mapping each listed source ID to its existing receipt path relative to the private store, for example `receipts/SRC-EXAMPLE/SV-EXAMPLE.json`. Supply exactly the ten registered sources. Do not copy public seed observations into files and represent them as original source bodies.
4. Run `python tools/hydra_constraint_semiconductor_pass006_capture_intake.py --private-root <private-store> --receipt-map <private-map.json> --release-id <owner-release-id> --created-at <actual-zoned-timestamp>`.

The intake preflights all receipts before writing the existing immutable T1 release format. It checks exact stored receipts and raw-byte digests through the T1 store, registry identity and locator, eligible disposition, contained paths, and acquisition/availability/release temporal order. For this reviewed-seed intake, availability must not precede the seed's conservative availability floor. Historical acquisition recovery belongs in its separately reviewed owner path.

## Validation and limits

Synthetic integration: ten persisted objects and receipts produce one valid stored release. Eleven negative cases reject incomplete coverage, unknown sources, wrong source mapping, wrong locator, quarantine, backdating, a premature release timestamp, tampered bytes, missing stored receipts, traversal and a symlink escape. Rejections create no release file.

Five CI workflows passed for the preceding Pass005 commit `f0ba30bdabc197bdc5b343196f9f43f6594852a4`. This pass adds its synthetic intake test to the existing second-slice workflow.

Real sources captured in this pass: zero. Canonical identities resolved: zero. Runtime admission: blocked. A valid T1 release still requires existing T2 normalization, identity resolution, owner conformance and downstream gates; it is not a semiconductor readiness certificate. Existing historical registries and reports remain unchanged.
