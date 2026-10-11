# Native T5-to-T6 V2 preparation note

**State:** preparation only; not an implementation, admission request, authority receipt, or successor batch record.

## Verified V1 baseline

The V1 package remains the baseline and must remain unchanged while V2 is prepared:

| Item | SHA-256 |
| --- | --- |
| Implementation manifest | `a7d6b72d94630dba06a612c966db22c733205ecc926117cd68e2979ad1ca9879` |
| Bridge artifact | `e090e1326ee4ff03fca378925b1316dd3c870ccf70a9fe313c9c8fb1e00e476f` |
| Test evidence | `d614733a65943334ab9a2f5c41b7b94b2d8a111d23953b79622a975d5a636294` |
| Admission request | `3b740fa86e605d4d56dd3d018a00482ff37e1ab19e0d5e4768e2cee62488f9a0` |

V1's manifest schema is `hydra-t5-t6-native-binding-implementation/v1`. Its three request flags are false: `runtime_activation_requested`, `canonical_promotion_requested`, and `live_source_requested`.

## V2 package shape

Once the intended semantic change is supplied, prepare new additive files for:

1. V2 bridge implementation and V2 behavior-specific tests.
2. A V2 implementation manifest and a new admission request, each with new IDs and hashes bound to the V2 artifact and tests.
3. Batch035 successor status artifacts: blocker register, master status, implementation presentation report, and artifact manifest.

Do not edit V1 or reuse its request, signature, or receipt. Keep runtime activation, canonical promotion, live-source request flags, and authorization limitation flags false. A repository-authored manifest or request is not an external signed authority receipt.

## Inputs still required

The V2 semantic delta has not been specified. Before implementation, record:

- The exact V1 behavior that changes and the intended V2 behavior.
- Inputs that trigger the change, including boundary and malformed cases.
- Required output or exception behavior, including ordering and determinism expectations.
- Behavior that must remain identical to V1.
- Regression cases and any new fixtures needed to demonstrate the delta.

Without these decisions, a V2 implementation and meaningful behavior-specific tests would be invented rather than derived from requirements.

## Known admission and evidence blockers

- The Batch021 status in this checkout says no signed admission receipt is present and implementation admission, runtime activation, canonical promotion, and historical replay are false.
- The Batch020 first-slice blocker register keeps PIT-002B historical availability evidence incomplete; raw materialization alone does not close it.
- Canonical evaluation and ordinary replay remain downstream of admission and historical-availability evidence.
- The Batch034 master status is present in `docs/constraint/architecture` and chains from Batch033. It is the latest successor record in this checkout; Batch035 is the next successor number. Preserve its blocked status unless new evidence changes it.

## Completion sequence

1. Specify and review the V2 semantic delta.
2. Implement the additive bridge and tests; verify the old V1 files remain byte-for-byte unchanged.
3. Compute fresh raw SHA-256 values and bind them into the V2 manifest and request.
4. Build Batch035 status artifacts against the Batch034 master status and Batch020 vertical blocker register.
5. Leave admission blocked until an authorized external receipt and separate historical-availability evidence are actually present.