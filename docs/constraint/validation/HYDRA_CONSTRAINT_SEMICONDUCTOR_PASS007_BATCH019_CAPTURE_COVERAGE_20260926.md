# HYDRA Constraint semiconductor Pass007 — Batch019 capture coverage

Reconciles main `56728be35094d44c5b7172c366f4924ebba10ac3`. Batch019 succeeds Batch018 as the current Thread6 population authority. Earlier Pass005 and Pass006 reports remain historical snapshots.

The private receipt intake now requires all 20 distinct source IDs from Batch018 (six), Batch019 (ten), and supplementary Pass004 (four). The Pass006 command names remain stable; `--list-sources` emits the current required set. A ten-receipt submission can no longer appear complete. Source IDs and source-version IDs retain their existing meanings. Runtime admission remains blocked.

Moved this lane's seed and receipt-intake checks into `.github/workflows/constraint-semiconductor-source-intake.yml`. The shared second-slice workflow is byte-identical to current main, retaining all Batch017/018/019 checks. This avoids repeatedly editing the same workflow sections as the Thread6 owner.

## Acquisition-path inspection

Inspected the capture owner branch at `0ef8dfb` (`constraint/t1-private-capture-execution-packet-20260926`). Its automated browser runner pins the power slice, nine sources and first-slice downstream checks; it must not be presented as a working semiconductor capture command. Its existing offline `first_slice_materialization.materialize_capture_plan` accepts matching nonempty registry/plan slice IDs and exact source coverage, so it is a viable reuse point after owner integration. No copy or replacement capture pipeline is introduced here.

The browser runner also infers PDF MIME from a `.pdf` URL suffix. The Micron prepared-remarks locator is extensionless; enabling semiconductor capture therefore needs explicit reviewed MIME handling in the existing runner, in addition to registry selection and downstream slice support. No actual capture or content-type confirmation is claimed in this pass.

## Verification

Batch019 validator and all 15 adversarial tests pass. Pass004 source validator and its 14 negative mutations pass. The intake test creates a valid synthetic 20-receipt release and rejects eleven invalid submissions without creating a release. All inputs are synthetic; real raw source bytes captured: zero. Existing source registry records and population authority artifacts are unchanged.
