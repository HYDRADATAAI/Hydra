# Semiconductor Pass012: Micron capture locator repair

The user reported six saved captures followed by a redirect-body failure. Their browser trace shows the old Micron Q2 FY2025 static-file locator redirecting to the generic investor overview, which embeds an unrelated Q3 FY2026 deck.

Pass012 preserves Pass009 and all seed registries. Its successor capture registry changes only the seventh source URL to Micron’s hosted archive, retaining the same document UUID. The archive PDF was reviewed as the ten-page Fiscal Q2 2025 Earnings Call Prepared Remarks dated March 20, 2025. No historical byte equivalence is asserted and no PDF bytes are committed.

The first six source rows, source ordering, declared MIME types, and review availability metadata remain unchanged. The existing SEMICONDUCTOR_PASS009 journal profile remains in use, so the unfinished six-entry journal can resume under Pass012 after validating its saved bytes. Exact locator, redirect, MIME, status and body checks remain enforced.

Validation: successor registry preflight and a synthetic six-entry resume test. Actual Windows acquisition of the replacement PDF remains unverified. Twenty successful captures and attestation are still required before a T1 release; T2 normalization and strict historical replay remain blocked. The separate Pass006 intake still pins seed URLs and will require explicit adoption of this reviewed locator supersession before accepting the replacement receipt.
