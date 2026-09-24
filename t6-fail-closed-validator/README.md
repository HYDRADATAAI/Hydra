# HYDRA T6 Fail-Closed Validator

Status: **SOURCE-ONLY REPAIR, DORMANT, NOT ACTIVATED**

This directory contains the fail-closed T6 validator source and a focused regression test for camelCase authority smuggling. The repair recognizes camelCase, PascalCase, separator-delimited, and punctuation-delimited forms of forbidden authority markers.

The validator still returns only `ABSTAIN` or `QUARANTINE`. It does not rank candidates, select canonical truth, mutate a canonical store, register itself in Thread F, or perform external effects.

Bound policies, schemas, oracle data, authority records, sealed review artifacts, reports, and external conformance fixtures are intentionally excluded from this public source repair.

## Test

```powershell
$env:PYTHONPATH=(Resolve-Path '.\src').Path
python -m unittest discover -s tests -t . -v
```
