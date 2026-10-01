# Thread G native receipt validation repair

Base: `ed690ddda710476ee6a051b77032f7d09a24d3d2`.

This repairs two input-validation defects in `native_binding_admission.py`:

- Dictionary equality treated numeric `0` and `0.0` as the required literal
  `false` for each of the five `limitations` fields. The repair checks the
  exact field set and requires each value to be `False` by identity.
- A non-list `supersession.chain` could be indexed after its type check had
  already failed. Objects, positive integers and `true`, with a predecessor,
  raised exceptions. The repair only indexes a list and preserves the
  previously recorded rejection for malformed chains.

The unmodified production source was tested first on Windows Server 2025,
Python 3.14.7, in run
https://github.com/HYDRADATAAI/Hydra/actions/runs/36933291480.
The 37 shape tests produced exactly 10 assertion failures and 3 errors; the
remaining 24 passed. The initial setup attempt, run 36933194474, stopped before
testing because of an existing long repository path. Enabling Git long-path
support in the disposable Windows runner resolved that setup failure.

`run_windows.py` repeats that pinned baseline and, when the source differs,
requires the shape tests, existing native-admission tests and existing bridge
tests all to pass without skips. It records exact commands, commits, tree,
test counts and before/after source hashes under
`D:\NYX_PORTABLE\THREAD_G_RECEIPT_REPAIR`. This is Windows-only validation.

The shape probes use a test double and no cryptographic signature. The
existing regression fixtures use public test keys. Neither is a real
authority decision. Positive synthetic fixture results must not be treated as
admission of the project implementation.

## Authority discovery remains unresolved

`IMPLEMENTATION_AUTHORITY_ROUTE=UNRESOLVED`

`IMPLEMENTATION_ADMITTED=NO`

No authority request has been sent. No real admission receipt has been created
or verified. A role string, filename, email-like string, commit signature,
test key, or historical mention does not designate a production authority.

The separately recorded Thread G V002 audit remains the detailed discovery
evidence. All 23 cited source files have identical bytes at the base above.
Its outstanding requirements are:

1. Authenticated principal identity and binding to `IMPLEMENTATION_CONTRACT`.
2. Designation record, authorized issuer/provenance, effective scope and validity.
3. Governed acceptance of the receipt envelope and signing profile.
4. Approved production verifier configuration bound to that principal and key.
5. Production `key_id`, applicable trust-root identifier/fingerprint/reference,
   principal-role-key binding, and current key lifecycle evidence.
6. An authentic receipt binding the exact implementation, manifest, artifact
   and test-evidence hashes already in the unsigned admission request.
7. Authenticated validity times and governed signing-time semantics. The
   existing receipt uses `issued_at`, `expires_at`, `revocation.checked_at`;
   adding a `signed_at` field would violate its current exact-key schema.
8. The approved recipient/service/channel/endpoint, its designation binding,
   and accepted transport/authentication procedure.
9. A current authentic positive receipt, and an approved rejection/response
   format where a rejection is returned.
10. Governed revocation source and retrieval binding, current authenticated
    status/time/sequence, and authority/key/receipt supersession evidence.

The implementation manifest, bridge, existing bridge test source, admission
request, and historical governed status records are unchanged by this repair.
This change does not assign an authority, select a production key or verifier,
establish a route, authorize submission, or advance any admission gate.
