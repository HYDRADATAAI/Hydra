NYX exact-C D continuation: validation-only, do not merge

This run executes D against immutable tested source e70f55110c4217905805678d0af279afd22e302a / tree01319aee05f317bcd6289db9eac2c94881b6d697.
It restores the exact633684-byte public archive from C run37145809514, SHA25678f728ea2bce4bc6d026642c94e1e33b4b5b5c57eaf8228489f6e18e32f3b0a1.
The archive contains C PASS535methods/797subtests/all15groups/40commands and the original D freshness failure. Neither historical record is rewritten.

All42 original D command labels and runtime checks remain. Separate preflight/postflight verify strict live main a2cb9ac, merged PR143 fd5bba4 and current PR146 a187adee refs.
Complete Git maps must prove main equals fd5 tree; main-to-tested source differs only by three reviewed workflow/writer repairs; tested source-to-current PR146 differs only by two reviewed stricter workflows, with all739 other paths exact.
C is not claimed to have executed on current PR146 a187adee. Its current workflow checks are separate evidence.

Report C_reference/ preserves the complete original archive contents; report/v006/ holds the new D results; preflight.json and postflight.json hold independent live/equivalence checks. A successful D report alone is insufficient if either surrounding check or the workflow fails.
The original33-file full harness and source bytes remain unchanged in the carrier. The separate branch triggers only the new continuation workflow.
All source, fixtures, temporary files and reports are on Windows D:. Public/synthetic data only. No source/runtime/test changes, admission, authority, private capture, merge or production action is performed.
