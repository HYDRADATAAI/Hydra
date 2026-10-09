"""Hosted-only, offline success-path proof against the checked-out PollRunner."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace


WAIT_SECONDS = 15
CAPTURED = "2026-10-09T12:00:00Z"
POLLING_PATH = "constraint-runtime/src/hydra_constraint/polling.py"
SOURCE_PINS = {
    "6f0c29ba4ff87388d7a478bbba06e21f983927a0": {
        "commit": "beec4ca5c1868d80c0452a2f8dba0fb2918f89be",
        "tree": "5c45534f08ae0cfaed686f29a6ae8eb0e76712a2",
    },
    "c23be5c0b2c0945c82721c06189c6df3a19128df": {
        "commit": "df2a5fbe6650296a37c9e2f77dabbdcabd931bcd",
        "tree": "ae56501a479f1f2cbecd8cfbc9f7d243341e652a",
    },
}


class InfrastructureFailure(RuntimeError):
    pass


class LiveWorkerFailure(InfrastructureFailure):
    pass


def require(condition, message):
    if not condition:
        raise InfrastructureFailure(message)


def wait_for(event, label):
    require(event.wait(WAIT_SECONDS), "liveness timeout: " + label)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def inventory(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])
    require(not git("status", "--porcelain").strip(), "checkout is not clean")
    files = {}
    for raw in git("ls-files", "-z").split(b"\0"):
        if raw:
            name = os.fsdecode(raw)
            path = root / name
            require(path.is_file() and not path.is_symlink(), "non-regular tracked file: " + name)
            files[name] = sha256(path.read_bytes())
    return {
        "head": git("rev-parse", "HEAD").decode().strip(),
        "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "files": files,
    }


class Trace:
    def __init__(self):
        self.guard = threading.Lock()
        self.rows = []

    def add(self, kind, **fields):
        with self.guard:
            row = {"index": len(self.rows), "kind": kind,
                   "worker": threading.current_thread().name, **fields}
            self.rows.append(row)
            return row

    def snapshot(self):
        with self.guard:
            return list(self.rows)


class Case:
    def __init__(self, path, concurrent):
        self.path = path
        self.concurrent = concurrent
        self.trace = Trace()
        self.first_parked = threading.Event()
        self.release_first = threading.Event()
        self.second_started = threading.Event()
        self.decision = threading.Event()
        self.reports = {}
        self.worker_errors = []
        self.result_guard = threading.Lock()
        self.lock_records = []

    def worker(self, runner, spec, label):
        try:
            self.trace.add("worker_start", source=spec.name)
            if label == "B":
                self.second_started.set()
            report = runner.poll(spec)
            with self.result_guard:
                self.reports[label] = report.to_dict()
            self.trace.add("poll_return", source=spec.name, status=report.status)
            if label == "B":
                self.decision.set()
        except BaseException as exc:
            with self.result_guard:
                self.worker_errors.append({"worker": label, "error": repr(exc)})
            self.trace.add("worker_exception", error=repr(exc))
            self.decision.set()


class ObservedLock:
    """Delegate to the same production-created lock; only observe ownership."""
    def __init__(self, original, case, label):
        self.original = original
        self.case = case
        self.label = label
        self.observation_guard = threading.Lock()
        self.owner = None
        require(type(original) is type(threading.Lock()), "expected an actual threading.Lock")
        case.lock_records.append({"label": label, "original_id": id(original)})

    def __enter__(self):
        worker = threading.current_thread().name
        acquired = self.original.acquire(blocking=False)
        if not acquired:
            with self.observation_guard:
                owner = self.owner
            self.case.trace.add("lock_contended", lock=self.label, owner=owner)
            if worker == "B" and owner == "A" and self.case.first_parked.is_set() and not self.case.release_first.is_set():
                self.case.decision.set()
            self.original.acquire()
        with self.observation_guard:
            require(self.owner is None, "observed ownership overlap")
            self.owner = worker
        self.case.trace.add("lock_enter", lock=self.label)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        worker = threading.current_thread().name
        with self.observation_guard:
            require(self.owner == worker, "wrong lock owner released")
            self.owner = None
        self.case.trace.add("lock_release_begin", lock=self.label)
        self.original.release()
        return False


def observe_source_locks(runner, case, names):
    if hasattr(runner, "_poll_lock"):
        runner._poll_lock = ObservedLock(runner._poll_lock, case, "runner")
        return "runner"
    require(hasattr(runner, "_source_request_lock") and hasattr(runner, "_source_locks"),
            "unrecognized source lock surface")
    originals = {name: runner._source_request_lock(name) for name in names}
    require(len({id(value) for value in originals.values()}) == len(names),
            "historical distinct names did not receive distinct source-created locks")
    for name, original in originals.items():
        runner._source_locks[name] = ObservedLock(original, case, name)
    return "per-name"


class Clock:
    def __init__(self):
        self.guard = threading.Lock()
        self.now = 0.0
        self.delays = []

    def monotonic(self):
        with self.guard:
            return self.now

    def sleep(self, seconds):
        require(seconds >= 0, "negative fixture sleep")
        with self.guard:
            self.delays.append(seconds)
            self.now += seconds


def fixture(label, number):
    accession = "0000000001-26-" + str(number).zfill(6)
    body = json.dumps({
        "cik": "1", "name": "R36 Fixture " + label,
        "filings": {"recent": {
            "accessionNumber": [accession], "form": ["8-K"],
            "filingDate": ["2026-10-09"], "reportDate": ["2026-10-09"],
            "primaryDocument": ["fixture.htm"],
        }},
    }, sort_keys=True, separators=(",", ":")).encode()
    return {"label": label, "body": body, "id": accession.replace("-", ""),
            "etag": "fixture-" + str(number), "url": "https://example.invalid/r36/" + label,
            "source": "source-" + label, "digest": sha256(body)}


class Transport:
    def __init__(self, polling, case, clock, fixtures):
        self.polling, self.case, self.clock = polling, case, clock
        self.fixtures = fixtures
        self.next = {}
        self.calls = []
        self.guard = threading.Lock()

    def fetch(self, url, headers=None, timeout=20):
        label = threading.current_thread().name
        with self.guard:
            index = self.next.get(label, 0)
            require(label in self.fixtures and index < len(self.fixtures[label]), "unexpected fixture request")
            record = self.fixtures[label][index]
            require(url == record["url"] and headers == {}, "unexpected transport arguments")
            self.next[label] = index + 1
            self.calls.append({"label": label, "index": index, "start": self.clock.monotonic()})
        self.case.trace.add("fetch", source=record["source"], external_id=record["id"])
        return self.polling.HttpResponse(url, 200, {"etag": record["etag"]}, record["body"], CAPTURED)


class DurableFixture:
    """A persisted fake durable boundary; not a production-ledger claim."""
    def __init__(self, case, records):
        self.case = case
        self.expected = {record["id"]: record for record in records}
        self.path = case.path / "adapted-rows.jsonl"
        self.guard = threading.Lock()
        self.ids = []

    def ingest_adapted(self, raw):
        label = threading.current_thread().name
        external_id = raw["external_record_id"]
        require(external_id in self.expected, "unexpected adapted ID")
        expected = self.expected[external_id]
        require(raw["event_key"] == "SEC:" + external_id and raw["adapter_name"] == "SECEdgarAdapter"
                and raw["headline"] == "R36 Fixture " + expected["label"] + " filed 8-K"
                and raw["captured_at"] == CAPTURED and raw["source_url"] == expected["url"]
                and raw["target"] == "R36_FIXTURE_TARGET", "real parser/adapter output mismatch")
        self.case.trace.add("append_enter", external_id=external_id)
        if self.case.concurrent and label == "A":
            self.case.trace.add("first_append_parked", external_id=external_id)
            self.case.first_parked.set()
            wait_for(self.case.release_first, "release first append")
            self.case.trace.add("first_append_released", external_id=external_id)
        with self.guard:
            require(external_id not in self.ids, "duplicate durable append")
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(raw, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.ids.append(external_id)
        self.case.trace.add("append_complete", external_id=external_id)
        return SimpleNamespace(action="APPEND")


def make_spec(polling, label):
    return polling.PollSpec(
        name="source-" + label, adapter="sec_edgar", source_class="sec_edgar",
        url="https://example.invalid/r36/" + label, parser="sec_json",
        cadence_minutes=1, stale_after_minutes=5, target="R36_FIXTURE_TARGET",
        jurisdiction="United States", max_rps=2,
        backoff=polling.BackoffPolicy(max_attempts=1),
    )


def setup_case(polling, persistence, path, concurrent):
    case, clock = Case(path, concurrent), Clock()
    records = [fixture("A", 1), fixture("B" if concurrent else "A", 2)]
    groups = {"A": [records[0]]}
    groups.setdefault(records[1]["label"], []).append(records[1])

    class ObservedCursors(persistence.CursorStore):
        def adapter(self, name):
            case.trace.add("cursor_read", source=name)
            return super().adapter(name)

    cursors = ObservedCursors(path / "cursor.json")
    archive = polling.RawArchive(path / "archive")
    durable = DurableFixture(case, records)
    transport = Transport(polling, case, clock, groups)
    original_atomic_json = polling._atomic_json

    def observe_atomic_json(target, value):
        original_atomic_json(target, value)
        if Path(target) == cursors.path:
            case.trace.add("cursor_persisted", state=json.loads(cursors.path.read_text()))

    polling._atomic_json = observe_atomic_json
    runner = polling.PollRunner(durable, cursors, archive, transport, sleeper=clock, clock=clock.monotonic)
    layout = observe_source_locks(runner, case, ["source-A", "source-B"] if concurrent else ["source-A"])
    return case, clock, records, cursors, durable, transport, runner, layout


def verify_success(case, persistence, records, cursors, durable, reports):
    require(not case.worker_errors, "worker exceptions: " + repr(case.worker_errors))
    require(len(reports) == len(records), "missing successful poll reports")
    expected_states = {}
    for record, report in zip(records, reports):
        source = record["source"]
        previous = expected_states.get(source)
        expected_report = {
            "source": source, "status": "PASS", "attempts": 1, "http_statuses": [200],
            "raw_hashes": [record["digest"]], "parsed_records": 1, "appended": 1,
            "skipped_seen": 0, "quarantined": 0,
            "cursor_before": previous["cursor"] if previous else None,
            "cursor_after": record["etag"], "captured_at": CAPTURED,
            "error": None, "backoff_delays": [],
        }
        require(report == expected_report, "unexpected successful report: " + repr(report))
        ids = (previous["seen_external_ids"] if previous else []) + [record["id"]]
        expected_states[source] = {
            "cursor": record["etag"], "last_seen_external_record_id": record["id"],
            "last_polled_at": CAPTURED, "last_success_at": CAPTURED, "last_error": None,
            "seen_external_ids": ids,
        }
        prefix = case.path / "archive" / source / "20261009" / record["digest"]
        require(prefix.with_suffix(".bin").read_bytes() == record["body"], "raw archive byte mismatch")
        metadata = json.loads(prefix.with_suffix(".json").read_text())
        require(metadata == {
            "source": source, "url": record["url"], "status": 200, "captured_at": CAPTURED,
            "attempt": 1, "sha256": record["digest"], "bytes": len(record["body"]),
            "headers": {"etag": record["etag"]},
            "body_file": source + "/20261009/" + record["digest"] + ".bin",
        }, "raw archive metadata mismatch")
    expected_state = {"format": "HYDRA_CONSTRAINT_CURSOR_V1", "adapters": expected_states}
    persisted = json.loads(cursors.path.read_text())
    reloaded = persistence.CursorStore(cursors.path).state
    require(persisted == reloaded == cursors.state == expected_state, "persisted/reloaded cursor state mismatch")
    adapted = [json.loads(line) for line in durable.path.read_text().splitlines()]
    expected_ids = sorted(record["id"] for record in records)
    require(sorted(row["external_record_id"] for row in adapted) == expected_ids == sorted(durable.ids),
            "persisted adapted IDs do not exactly match fixtures")
    require(len([row for row in case.trace.snapshot() if row["kind"] == "cursor_persisted"]) == 2,
            "expected two observed real cursor writes")
    return {"reports": reports, "cursor_state": persisted, "adapted_ids": durable.ids,
            "adapted_rows_sha256": sha256(durable.path.read_bytes()),
            "fixture_sha256": [record["digest"] for record in records]}


def sequential(polling, persistence, path):
    case, clock, records, cursors, durable, transport, runner, layout = setup_case(polling, persistence, path, False)
    original_name = threading.current_thread().name
    try:
        threading.current_thread().name = "A"
        reports = [runner.poll(make_spec(polling, "A")).to_dict() for _ in records]
    finally:
        threading.current_thread().name = original_name
    verified = verify_success(case, persistence, records, cursors, durable, reports)
    require([call["start"] for call in transport.calls] == [0.0, 0.5] and clock.delays == [0.5],
            "sequential successful pacing mismatch")
    return {"case": "sequential_successful_polls", "result": "PASS", "mechanism": "two_successes_exact_pacing_and_persistence",
            "lock_layout": layout, "requests": transport.calls, "delays": clock.delays,
            "locks": case.lock_records, "trace": case.trace.snapshot(), **verified}


def concurrent(polling, persistence, path):
    case, clock, records, cursors, durable, transport, runner, layout = setup_case(polling, persistence, path, True)
    workers = [threading.Thread(target=case.worker, args=(runner, make_spec(polling, label), label),
                                name=label, daemon=True) for label in ("A", "B")]
    started = []
    decision_rows = []
    try:
        workers[0].start(); started.append(workers[0])
        wait_for(case.first_parked, "first inside durable append")
        workers[1].start(); started.append(workers[1])
        wait_for(case.second_started, "second public poll started")
        wait_for(case.decision, "positive contention or second completed")
        require(not case.worker_errors, "worker failed before concurrency decision")
        require(case.first_parked.is_set() and not case.release_first.is_set(), "first append not parked at decision")
        decision_rows = case.trace.snapshot()
    finally:
        case.trace.add("release_first_requested")
        case.release_first.set()
        for worker in started:
            worker.join(WAIT_SECONDS)
        if any(worker.is_alive() for worker in started):
            raise LiveWorkerFailure("worker did not terminate after append release and join")
    reports = [case.reports.get(label) for label in ("A", "B")]
    verified = verify_success(case, persistence, records, cursors, durable, reports)
    before = [row for row in decision_rows if row["worker"] == "B"]
    b_work = [row for row in before if row["kind"] in {"cursor_read", "fetch", "append_enter", "append_complete", "poll_return"}]
    contention = [row for row in before if row["kind"] == "lock_contended" and row["owner"] == "A"]
    b_complete = [row for row in before if row["kind"] == "poll_return" and row["status"] == "PASS"]
    if contention and not b_work:
        result, mechanism = "PASS", "second_contended_on_actual_first_owned_lock_until_append_release"
    elif b_complete and all(any(row["kind"] == kind for row in b_work) for kind in ("cursor_read", "fetch", "append_enter", "append_complete")):
        result, mechanism = "FAIL", "second_successful_transaction_completed_while_first_append_parked"
    else:
        raise InfrastructureFailure("no recognized positive concurrency outcome: " + repr(before))
    trace = case.trace.snapshot()
    release_index = next(row["index"] for row in trace if row["kind"] == "release_first_requested")
    if result == "PASS":
        a_writes = [row for row in trace if row["worker"] == "A" and row["kind"] == "cursor_persisted"]
        require(len(a_writes) == 1 and a_writes[0]["index"] > release_index,
                "missing first cursor persistence after append release")
        require(a_writes[0]["state"]["adapters"] == {"source-A": verified["cursor_state"]["adapters"]["source-A"]},
                "first real cursor write did not persist exactly the first successful source")
        require(all(row["index"] > release_index for row in trace if row["worker"] == "B" and row["kind"] in {"cursor_read", "fetch", "append_enter", "append_complete"}),
                "second successful state access preceded release despite contention")
        require(all(row["index"] > a_writes[0]["index"] for row in trace if row["worker"] == "B" and row["kind"] in {"cursor_read", "fetch", "append_enter", "append_complete"}),
                "second state access preceded first real cursor persistence")
    require(len(transport.calls) == 2 and clock.delays == [], "unexpected two-name request activity")
    return {"case": "distinct_source_successful_transactions", "result": result, "mechanism": mechanism,
            "lock_layout": layout, "locks": case.lock_records, "decision_trace": decision_rows,
            "trace": trace, "requests": transport.calls, "delays": clock.delays, **verified}


def main():
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux",
            "hosted Linux validation only")
    require(sys.dont_write_bytecode, "invoke with python -B")
    root = Path(__file__).resolve().parents[1]
    before = inventory(root)
    module_blob = blob_sha((root / POLLING_PATH).read_bytes())
    require(module_blob in SOURCE_PINS, "unreviewed PollRunner source blob")
    denied_network = []

    def network_guard(event, args):
        if event.startswith("socket."):
            denied_network.append(event)
            raise InfrastructureFailure("network forbidden: " + event)

    sys.addaudithook(network_guard)
    sys.path.insert(0, str(root / "constraint-runtime" / "src"))
    polling = importlib.import_module("hydra_constraint.polling")
    persistence = importlib.import_module("hydra_constraint.persistence")
    for module in (polling, persistence):
        require(Path(module.__file__).resolve().is_relative_to(root / "constraint-runtime" / "src"), "import escaped exact checkout")
    original_cwd = Path.cwd()
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="r36-poll-", dir=os.environ["RUNNER_TEMP"]) as raw:
            temp = Path(raw).resolve()
            require(not temp.is_relative_to(root), "fixture directory is inside checkout")
            os.chdir(temp)
            for name, function in (("sequential_successful_polls", sequential), ("distinct_source_successful_transactions", concurrent)):
                case_path = temp / name
                case_path.mkdir()
                original_atomic_json = polling._atomic_json
                try:
                    row = function(polling, persistence, case_path)
                except LiveWorkerFailure as exc:
                    print(json.dumps({"case": name, "result": "INFRASTRUCTURE_FAIL",
                                      "mechanism": "live_worker_after_join", "error": repr(exc)}), flush=True)
                    # No hook restoration or fixture cleanup while any worker remains alive.
                    # The independent carrier always-step still checks checkout preservation.
                    os._exit(2)
                except BaseException as exc:
                    row = {"case": name, "result": "INFRASTRUCTURE_FAIL", "error": repr(exc)}
                finally:
                    polling._atomic_json = original_atomic_json
                results.append(row)
                print(json.dumps(row, sort_keys=True), flush=True)
    finally:
        os.chdir(original_cwd)
        after = inventory(root)
        require(after == before, "tracked source identity or byte inventory changed")
        require(not denied_network, "network operation was attempted")
        print(json.dumps({"source_head": before["head"], "source_tree": before["tree"],
                          "reviewed_source": SOURCE_PINS[module_blob], "polling_blob": module_blob,
                          "source_unchanged": True, "network_attempts": 0,
                          "tracked_files": len(before["files"])}), flush=True)
    totals = {"cases": len(results), "passed": sum(row["result"] == "PASS" for row in results),
              "failed": sum(row["result"] == "FAIL" for row in results),
              "infrastructure_failures": sum(row["result"] == "INFRASTRUCTURE_FAIL" for row in results)}
    print(json.dumps(totals, sort_keys=True), flush=True)
    return 0 if totals == {"cases": 2, "passed": 2, "failed": 0, "infrastructure_failures": 0} else 1


if __name__ == "__main__":
    raise SystemExit(main())
