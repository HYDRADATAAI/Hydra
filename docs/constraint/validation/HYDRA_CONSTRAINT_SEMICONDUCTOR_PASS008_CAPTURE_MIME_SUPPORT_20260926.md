# HYDRA Constraint semiconductor Pass008 — declared capture MIME support

Based on capture-owner commit `0ef8dfb1a0be9c78a7fde88d523b65b08671404e`. This change extends the existing browser runner, rather than adding another acquisition pipeline.

A source registry row may declare `expected_content_type` as exactly `application/pdf` or `text/html`. Omitted declarations retain the existing suffix-based behavior. Unsupported declarations fail registry preflight before browser acquisition. Fresh captures use the declaration for file extension and response validation; resumed captures revalidate against the same declaration.

The declaration does not authorize redirects, change the exact source locator, accept HTTP failures, bypass PDF signatures/size checks, or weaken HTML challenge-page rejection. It does not verify that a response is semantically the intended document; existing source review remains necessary.

This resolves the extensionless-document format prerequisite identified in Pass007. It does not enable semiconductor registry selection in the nine-source first-slice runner. No semiconductor source metadata was changed and no actual source bodies were captured.

Validation: `PYTHONPATH=constraint-t1-raw-artifact-store/src python3 -m unittest discover -s constraint-t1-raw-artifact-store/tests -q` ran 116 tests successfully with one environment-dependent skip. New regression coverage includes extensionless PDF acceptance, unchanged defaults, invalid declarations, response status/locator/redirect/signature/size rejection, and resumed-capture declaration consistency.

The accompanying Pass008 manifest binds changed implementation and test files. Earlier manifests remain historical snapshots at their original commits.
