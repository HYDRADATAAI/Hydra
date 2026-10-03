"""Exact test-only recovery of predecessor source metadata; no admission authority."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / 'docs/constraint/validation/HYDRA_CONSTRAINT_T1_BATCH033_CUSTODY_CONTINUATION_V001_20260928.json'
EXPECTED = {
    "schema": "HYDRA_CONSTRAINT_T1_BATCH033_CUSTODY_CONTINUATION_V1",
    "scope": "EXACT_MAIN_CUSTODY_METADATA_CONTINUATION",
    "predecessor_main_commit": "972f5f7e3d0fe0ae51f509f40be6e5c41a349819",
    "authoritative_main_commit": "bf74ad8352cc8681b374e185772085212619f00f",
    "original_timestamp_integration_head": "4a6b3e9f2ea992f833d2a7c0eba052508439d333",
    "source_owner_changes_preserved": True,
    "historical_predecessor_bytes_recoverable_exactly": True,
    "purpose": "VERIFY_PREVIOUS_BYTE_PINS_ONLY",
    "acceptance_effect": "NONE",
    "trusted_timestamp_verifier": "NOT_IMPLEMENTED",
    "historical_availability_promoted": False,
    "ordinary_replay_promoted": False,
    "canonical_admission_promoted": False,
    "private_capture_authorized": False,
    "api_export_binding": {
        "path": "constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/__init__.py",
        "git_blob_sha": "407435b4e0fa76e5cdc551e65d973d3a859daee1",
        "sha256": "7c68bac26ce4933bec6d1db9edd0fc02f3ca9b9d517fd189f77873a80c1db102"
    },
    "preserved_records": [
        {
            "path": "docs/constraint/validation/HYDRA_CONSTRAINT_T1_BATCH018_PUBLIC_HASH_SUCCESSOR_V001_20260928.json",
            "sha256": "dbe9a3b77a088b6e4106016e6e35623008f2d4ec913a5b7a0f1942e1daaf64f9"
        },
        {
            "path": "docs/constraint/validation/HYDRA_CONSTRAINT_T1_TIMESTAMP_GATE_SUCCESSOR_V001_20260927.json",
            "sha256": "8a5d61d50edd88f8e9f3fba50cf8481e30784681b11fa8ed0da521f5a24b07d0"
        },
        {
            "path": "docs/constraint/validation/HYDRA_CONSTRAINT_T1_TIMESTAMP_VALIDATOR_SUCCESSOR_V001_20260927.json",
            "sha256": "a2e7fcbb185ac7fbb89da3f8b919519322286487e0070a309b02aac186fb5d9f"
        }
    ],
    "transitions": [
        {
            "path": "docs/constraint/implementation/HYDRA_CONSTRAINT_T1_T2_PERSISTED_CUSTODY_SUPERSESSION_V001_20260926.json",
            "predecessor_sha256": "03e54ee2a1e0bbae2a7392ff2b274d10c1863dd494b75d41b7aa65eccb0a38d4",
            "successor_sha256": "c558f17ab77fb8af37a523a998eea0b08517945598df715ede846601217afce6",
            "predecessor_git_blob_sha": "fc6568c002f75e621d0b93da7443f291ad963a8a",
            "successor_git_blob_sha": "b4a0d35b992abfa9c114f7595acd24b6aaa9cddf",
            "replacement": {
                "before": "      \"successor_git_blob_sha\": \"8b773956010afc0cc502cfa3c4f266b7c31d2c6f\"\n    }\n  ],\n  \"guardrails\": [\n    \"SEAL",
                "after": "      \"successor_git_blob_sha\": \"8b773956010afc0cc502cfa3c4f266b7c31d2c6f\"\n    },\n    {\n      \"path\": \"constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/__init__.py\",\n      \"predecessor_git_blob_sha\": \"9edd2a2c99659d75a232ac06eefe053b0ee1b02d\",\n      \"successor_git_blob_sha\": \"407435b4e0fa76e5cdc551e65d973d3a859daee1\"\n    }\n  ],\n  \"guardrails\": [\n    \"SEAL"
            }
        },
        {
            "path": "docs/constraint/validation/HYDRA_CONSTRAINT_BATCH017_T1_PRIVATE_RECORD_SUPERSESSION_MAP_V001_20260926.json",
            "predecessor_sha256": "9f214731ff90b9690a3e25d730fe22ae275be988ce7bbd8edd252ec640eb8bbe",
            "successor_sha256": "0f187602898b1a900c10e67ed00116ca491cc8024d9d981140614185d3498dba",
            "predecessor_git_blob_sha": "006ac598fe6b4ba02d2d256932682eb12496e83b",
            "successor_git_blob_sha": "f057925fa54db6a22502c2c3bb48616234ff6c76",
            "replacement": {
                "before": "plementation version from 0.1.0 to 0.2.0 for persisted-custody hardening.\"\n    }\n  ],\n  \"guardrails\": [\n    \"NO_",
                "after": "plementation version from 0.1.0 to 0.2.0 for persisted-custody hardening.\"\n    },\n    {\n      \"path\": \"constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/__init__.py\",\n      \"predecessor_git_blob_sha\": \"9edd2a2c99659d75a232ac06eefe053b0ee1b02d\",\n      \"successor_git_blob_sha\": \"407435b4e0fa76e5cdc551e65d973d3a859daee1\",\n      \"reason\": \"Expose the generic ordinary-T2 source-version lineage API without changing persisted-custody, replay, or admission authority.\"\n    }\n  ],\n  \"guardrails\": [\n    \"NO_"
            }
        },
        {
            "path": "docs/constraint/validation/HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json",
            "predecessor_sha256": "bcf73e2977654aff87e34cd629089f59e7a41ae282c697e079257c3bdb06208b",
            "successor_sha256": "7461a5080e017590314f87b6c6bd59a4aa921d09eef219305fd69413769eac77",
            "predecessor_git_blob_sha": "4cfd44eb9362fafd18680501327b70d446a38273",
            "successor_git_blob_sha": "31049342e544766700ecf99324fe639cc5c6bb74",
            "replacement": {
                "before": "\": \"dd672a59f40d6d864d59c7692f07358d524e3264\",\n      \"successor_git_blob_sha\": \"006ac598fe6b4ba02d2d256932682eb12496e83b\"\n    },\n    {\n      \"path\": \"tools/vali",
                "after": "\": \"dd672a59f40d6d864d59c7692f07358d524e3264\",\n      \"successor_git_blob_sha\": \"f057925fa54db6a22502c2c3bb48616234ff6c76\"\n    },\n    {\n      \"path\": \"tools/vali"
            }
        }
    ]
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_record():
    try:
        return json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AssertionError("Batch033 continuation record unavailable") from exc


def verified_record():
    record = load_record()
    require(json.dumps(record, sort_keys=True) == json.dumps(EXPECTED, sort_keys=True),
            "Batch033 continuation record drifted")
    for pinned in EXPECTED["preserved_records"]:
        require(digest((ROOT / pinned["path"]).read_bytes()) == pinned["sha256"],
                "historical continuation record bytes changed")
    api = EXPECTED["api_export_binding"]
    data = (ROOT / api["path"]).read_bytes()
    require(digest(data) == api["sha256"] and git_blob(data) == api["git_blob_sha"],
            "Batch033 API export binding drifted")
    return record


def recover_predecessor_bytes(path, current=None):
    record = verified_record()
    matches = [t for t in record["transitions"] if path == ROOT / t["path"]]
    require(len(matches) == 1, "path is outside the exact Batch033 continuation")
    transition = matches[0]
    data = path.read_bytes() if current is None else current
    require(digest(data) == transition["successor_sha256"] and
            git_blob(data) == transition["successor_git_blob_sha"], "Batch033 successor bytes drifted")
    edit = transition["replacement"]
    before, after = edit["before"].encode("utf-8"), edit["after"].encode("utf-8")
    require(data.count(after) == 1, "Batch033 continuation anchor is not unique")
    prior = data.replace(after, before, 1)
    require(digest(prior) == transition["predecessor_sha256"] and
            git_blob(prior) == transition["predecessor_git_blob_sha"], "Batch033 predecessor bytes differ")
    return prior
