"""Hosted-only, offline durable source-rank recovery equivalence proof."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback


SOURCE_HEAD = "d291b79f8e105d2ca4668345f3ee482ae15224bc"
SOURCE_TREE = "5364b18b6276e94696273aa45d5b3d44401b0be7"
BASE_LEAVES = 771
HARNESS = "tools/test_ledger_rank_recovery_regression.py"
CARRIER = ".github/workflows/validation-ledger-rank-recovery.yml"
REPAIR_PATH = "constraint-runtime/src/hydra_constraint/persistence.py"
GRAPH = {"nodes": [{"node_id": "MAT_GALLIUM", "node_class": "material",
                    "name": "Gallium", "jurisdiction": "Global"}], "edges": []}
PRIORITIES = {"federal_register": 100, "secondary_report": 40}
ORIGINAL_DATE = "2026-10-15T00:00:00Z"
CHANGED_DATE = "2026-10-01T00:00:00Z"
CASES = (
    {"id": "official_only_control", "classes": ("federal_register",),
     "incoming_class": "secondary_report", "priority": 100, "action": "QUARANTINE"},
    {"id": "upward_merge_control", "classes": ("secondary_report", "federal_register"),
     "incoming_class": "federal_register", "priority": 100, "action": "CORRECT"},
    {"id": "downward_merge_regression", "classes": ("federal_register", "secondary_report"),
     "incoming_class": "secondary_report", "priority": 100, "action": "QUARANTINE"},
    {"id": "retraction_reset_control", "classes": ("federal_register",), "retract": True,
     "incoming_class": "secondary_report", "priority": 40, "action": "CORRECT"},
)


class InfrastructureFailure(RuntimeError):
    pass


def need(value, message):
    if not value:
        raise InfrastructureFailure(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_hash(value):
    return digest(canonical(value))


def root_path():
    return Path(__file__).resolve().parents[1]


def hosted_guard():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Windows",
         "hosted Windows execution only")
    need(sys.dont_write_bytecode and sys.flags.isolated, "python -I -B required")


def inventory():
    root = root_path()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])
    need(not git("status", "--porcelain", "--untracked-files=all").strip(), "source must be clean")
    head = git("rev-parse", "HEAD").decode().strip()
    need(head == os.environ["EXPECTED_HEAD"], "unexpected candidate HEAD")
    need(git("rev-parse", SOURCE_HEAD + "^{tree}").decode().strip() == SOURCE_TREE, "frozen source tree mismatch")
    def leaves(ref):
        result = {}
        for row in git("ls-tree", "-rz", ref).split(b"\0"):
            if row:
                metadata, path = row.split(b"\t", 1)
                mode, kind, sha = metadata.decode().split()
                name = path.decode("utf-8")
                need(mode == "100644" and kind == "blob", "unexpected leaf type/mode: " + name)
                result[name] = {"mode": mode, "type": kind, "sha": sha}
        return result
    baseline, current = leaves(SOURCE_HEAD), leaves("HEAD")
    need(len(baseline) == BASE_LEAVES, "frozen source leaf count changed")
    need(set(current) - set(baseline) == {HARNESS, CARRIER} and not set(baseline) - set(current),
         "candidate path inventory differs from frozen source plus proof")
    changes = {name: {"source": baseline[name], "candidate": current[name]}
               for name in baseline if baseline[name] != current[name]}
    need(set(changes).issubset({REPAIR_PATH}), "production delta exceeds one permitted persistence path")
    disk = {}
    for name in current:
        path = root / name
        need(path.is_file() and not path.is_symlink(), "nonregular source: " + name)
        raw = path.read_bytes()
        disk[name] = digest(raw)
        actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        need(actual_blob == current[name]["sha"], "checkout bytes differ from committed blob: " + name)
    return {"head": head, "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
            "baseline_head": SOURCE_HEAD, "baseline_tree": SOURCE_TREE, "leaves": current,
            "disk_sha256": disk, "source_changes": changes, "leaf_count": len(current)}


def snapshot_path():
    return Path(os.environ["RUNNER_TEMP"]) / "r39-ledger-rank-source-before.json"


def record_before():
    value = inventory()
    snapshot_path().write_bytes(canonical(value))
    print(json.dumps({"source_before": value}, sort_keys=True), flush=True)


def verify_after():
    before = json.loads(snapshot_path().read_bytes())
    after = inventory()
    need(after == before, "complete source inventory changed during proof")
    print(json.dumps({"source_preservation": "PASS", "head": after["head"], "tree": after["tree"],
                      "leaf_count": after["leaf_count"], "inventory_sha256": object_hash(after)}, sort_keys=True), flush=True)


def raw_fixture(case_id, source_class, index, *, conflict=False):
    return {"headline": "synthetic offline rank recovery fixture", "event_key": "R39-" + case_id,
            "event_type": "material_export_control", "target": "Gallium", "jurisdiction": "Global",
            "occurred_at": "2026-09-29T12:00:00Z", "known_at": "2026-09-29T12:01:00Z",
            "effective_at": CHANGED_DATE if conflict else ORIGINAL_DATE,
            "captured_at": "2026-09-29T12:" + str(2 + index).zfill(2) + ":00Z",
            "source_id": "SYNTH_" + str(index), "external_record_id": case_id + "-" + str(index),
            "source_class": source_class, "source_priority": PRIORITIES[source_class],
            "evidence_class": "A1" if source_class == "federal_register" else "B1", "severity": 0.8}


def persisted_snapshot(runtime, fingerprint):
    raw = runtime.store.path.read_bytes()
    need(raw.endswith(b"\n"), "durable JSONL lacks trailing newline")
    rows = [json.loads(line) for line in raw.splitlines()]
    need(rows == runtime.store.load_raw() == runtime.ledger.to_jsonable(), "disk/runtime entries differ")
    previous = "GENESIS"
    for index, row in enumerate(rows, 1):
        need(row["sequence"] == index and row["fingerprint"] == fingerprint, "sequence/fingerprint mismatch")
        need(row["source_class"] in PRIORITIES and row["source_priority"] == PRIORITIES[row["source_class"]],
             "persisted class/rank is not a legitimate fixture class/rank")
        need(row["prior_entry_hash"] == previous, "independent previous hash mismatch")
        need(row["payload_hash"] == object_hash(row["payload"]), "independent payload hash mismatch")
        unsigned = {key: value for key, value in row.items() if key not in {"payload", "entry_hash"}}
        need(row["entry_hash"] == object_hash(unsigned), "independent unsigned entry hash mismatch")
        previous = row["entry_hash"]
    chain = runtime.ledger.verify_chain()
    need(chain["status"] == "PASS" and chain["entries"] == len(rows) and chain["tip_hash"] == previous,
         "actual ledger verification failed")
    checkpoint = runtime.checkpoints.load()
    need(checkpoint["ledger_entries"] == len(rows) and checkpoint["ledger_tip_hash"] == previous,
         "checkpoint does not bind durable entries")
    need(checkpoint["active_events"] == runtime.ledger.active_events(), "checkpoint active events mismatch")
    state = runtime.ledger._active[fingerprint]
    return {"rows": rows, "jsonl_sha256": digest(raw), "tip_hash": previous, "chain": chain,
            "checkpoint_sha256": digest(runtime.checkpoints.path.read_bytes()),
            "active_events": runtime.ledger.active_events(),
            "active_state": {"priority": state["priority"], "sequence": state["sequence"],
                             "retracted": state["retracted"], "event": state["event"].to_dict()}}


def execute_case(case, directory, EventNormalizer, DurableLedgerRuntime):
    directory.mkdir()
    live = DurableLedgerRuntime(EventNormalizer(GRAPH), directory / "live" / "ledger.jsonl",
                                directory / "live" / "checkpoint.json")
    need(live.recover()["status"] == "PASS", "empty runtime recovery failed")
    seeds = [raw_fixture(case["id"], source_class, index) for index, source_class in enumerate(case["classes"])]
    entries = [live.ingest_adapted(raw) for raw in seeds]
    need([entry.action for entry in entries] == ["CREATE"] + ["MERGE_SOURCE"] * (len(entries) - 1),
         "seed did not produce the required legitimate CREATE/MERGE_SOURCE history")
    fingerprint = entries[0].fingerprint
    if case.get("retract"):
        entry = live.ledger.retract(fingerprint, recorded_at="2026-09-29T12:05:00Z",
                                    source_class="secondary_report", source_id="SYNTH_RETRACT",
                                    external_record_id=case["id"] + "-retract", reason="synthetic reset control")
        live.store.append(entry)
        live.checkpoints.save(live.ledger)
        need(entry.action == "RETRACT", "actual retraction action missing")
    before_live = persisted_snapshot(live, fingerprint)
    recovered = DurableLedgerRuntime(EventNormalizer(GRAPH), directory / "recovered" / "ledger.jsonl",
                                     directory / "recovered" / "checkpoint.json")
    ledger_bytes = live.store.path.read_bytes()
    checkpoint_bytes = live.checkpoints.path.read_bytes()
    recovered.store.path.write_bytes(ledger_bytes)
    recovered.checkpoints.path.write_bytes(checkpoint_bytes)
    report = recovered.recover()
    need(report["status"] == "PASS" and report["chain_status"] == "PASS" and report["checkpoint_state"] == "MATCH",
         "recovered checkpoint/chain did not match valid persisted history")
    need(recovered.store.path.read_bytes() == ledger_bytes, "recovery changed JSONL bytes")
    need(recovered.checkpoints.path.read_bytes() == checkpoint_bytes, "recovery changed matching checkpoint bytes")
    before_recovered = persisted_snapshot(recovered, fingerprint)
    need(before_live["rows"] == before_recovered["rows"] and before_live["tip_hash"] == before_recovered["tip_hash"],
         "recovery does not start with exact same valid entries/tip")
    continuation = raw_fixture(case["id"], case["incoming_class"], 8, conflict=True)
    # Observe both decisions even when rank has already diverged; do not preempt the behavioral proof.
    next_live = live.ingest_adapted(continuation)
    next_recovered = recovered.ingest_adapted(continuation)
    after_live = persisted_snapshot(live, fingerprint)
    after_recovered = persisted_snapshot(recovered, fingerprint)
    need(next_live.fingerprint == next_recovered.fingerprint == fingerprint, "continuation changed event identity")
    expected_date = ORIGINAL_DATE if case["action"] == "QUARANTINE" else CHANGED_DATE
    checks = {
        "live_pre_rank": before_live["active_state"]["priority"] == case["priority"],
        "recovered_pre_rank": before_recovered["active_state"]["priority"] == case["priority"],
        "pre_state_equal": before_live == before_recovered,
        "retraction_state": before_live["active_state"]["retracted"] == before_recovered["active_state"]["retracted"] == bool(case.get("retract")),
        "live_decision": next_live.action == case["action"],
        "recovered_decision": next_recovered.action == case["action"],
        "live_active_date": [row["effective_at"] for row in after_live["active_events"]] == [expected_date],
        "recovered_active_date": [row["effective_at"] for row in after_recovered["active_events"]] == [expected_date],
        "complete_final_state_equal": after_live == after_recovered,
    }
    observation = {"case": case["id"], "expected_priority": case["priority"], "expected_action": case["action"],
                   "seed_inputs": seeds, "continuation_input": continuation, "recovery": report,
                   "before": {"live": before_live, "recovered": before_recovered},
                   "after": {"live": after_live, "recovered": after_recovered},
                   "decisions": {"live": next_live.action, "recovered": next_recovered.action}, "checks": checks,
                   "result": "PASS" if all(checks.values()) else "FAIL"}
    return observation


def run_cases():
    root = root_path()
    before = json.loads(snapshot_path().read_bytes())
    need(before["head"] == os.environ["EXPECTED_HEAD"], "source snapshot is not this candidate")
    attempts = []
    def guard(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty", "pty.spawn"}:
            attempts.append(event)
            raise InfrastructureFailure("network/process launch forbidden in fixture: " + event)
    sys.addaudithook(guard)
    source = root / "constraint-runtime" / "src"
    sys.path.insert(0, str(source))
    module = importlib.import_module("hydra_constraint")
    imported = {}
    for name, value in sorted(sys.modules.items()):
        if name == "hydra_constraint" or name.startswith("hydra_constraint."):
            file = Path(value.__file__).resolve()
            need(file.is_relative_to(source), "production import escaped exact candidate")
            relative = file.relative_to(root).as_posix()
            need(digest(file.read_bytes()) == before["disk_sha256"][relative], "import source differs from snapshot")
            imported[relative] = digest(file.read_bytes())
    need(module.SOURCE_PRIORITY["federal_register"] == 100 and module.SOURCE_PRIORITY["secondary_report"] == 40,
         "fixture rank mapping does not match actual source policy")
    results = []
    with tempfile.TemporaryDirectory(prefix="r39-rank-", dir=os.environ["RUNNER_TEMP"]) as temporary:
        directory = Path(temporary).resolve()
        need(not directory.is_relative_to(root), "runtime state must remain outside source")
        for case in CASES:
            try:
                value = execute_case(case, directory / case["id"], module.EventNormalizer, module.DurableLedgerRuntime)
            except Exception as exc:
                value = {"case": case["id"], "result": "INFRASTRUCTURE_ERROR",
                         "error": type(exc).__name__ + ": " + str(exc), "traceback": traceback.format_exc()}
            results.append(value)
            print(json.dumps({"rank_recovery_case": value}, sort_keys=True), flush=True)
    need(not attempts, "fixture attempted network/process operation")
    summary = {"cases": len(results), "pass": sum(row["result"] == "PASS" for row in results),
               "fail": sum(row["result"] == "FAIL" for row in results),
               "infrastructure_errors": sum(row["result"] == "INFRASTRUCTURE_ERROR" for row in results),
               "network_attempts": len(attempts), "imported_sources": imported,
               "head": before["head"], "tree": before["tree"]}
    print(json.dumps({"rank_recovery_summary": summary}, sort_keys=True), flush=True)
    return 1 if summary["fail"] or summary["infrastructure_errors"] else 0


def main():
    hosted_guard()
    need(len(sys.argv) == 2, "exactly one mode required")
    if sys.argv[1] == "before":
        record_before()
        return 0
    if sys.argv[1] == "after":
        verify_after()
        return 0
    need(sys.argv[1] == "run", "unknown mode")
    return run_cases()


if __name__ == "__main__":
    raise SystemExit(main())
