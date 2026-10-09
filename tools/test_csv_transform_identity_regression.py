"""Hosted, offline comparison of exact pre-fix and candidate CSV transforms."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


BASE_HEAD = "79f36544168e1d54e20bf644348d0cc82c5cf1cf"
BASE_TREE = "b6ecaaff8519e73d2a1c08656907878dea5e97b0"
COLUMNS = ("source_system", "source_record_id", "symbol", "event_time", "price", "volume", "currency", "venue")
VALUES = ("SYNTH_A", "fixture-1", "AAA.US", "2026-10-09T12:00:00Z", "1.25", "10", "usd", "xnas")
ALIASES = {"AAA.US": "AAA", "EEE.US": "EEE"}
MISSING_ERRORS = sorted(("source_system_missing", "source_record_id_missing", "symbol_missing",
                         "event_time_missing", "price_missing", "volume_missing", "currency_invalid", "venue_invalid"))


class InfrastructureFailure(RuntimeError):
    pass


def need(value, message):
    if not value:
        raise InfrastructureFailure(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def object_digest(value):
    return digest(canonical(value))


def hosted_guard():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux",
         "hosted Linux execution only")
    need(sys.dont_write_bytecode, "python -B required")


def inventory(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])
    need(not git("status", "--porcelain").strip(), "source checkout is dirty")
    files = {}
    for raw in git("ls-files", "-z").split(b"\0"):
        if raw:
            name = os.fsdecode(raw)
            path = root / name
            need(path.is_file() and not path.is_symlink(), "nonregular tracked source " + name)
            files[name] = digest(path.read_bytes())
    return {"head": git("rev-parse", "HEAD").decode().strip(),
            "tree": git("rev-parse", "HEAD^{tree}").decode().strip(), "files": files}


def fixtures(directory):
    row = ",".join(VALUES) + "\n"
    data = {"unpadded": (",".join(COLUMNS) + "\n" + row).encode(),
            "padded": (",".join(" " + item + " " for item in COLUMNS) + "\n" + row).encode()}
    for name, value in data.items():
        (directory / (name + ".csv")).write_bytes(value)
    (directory / "aliases.json").write_bytes(canonical(ALIASES))
    return {path.name: digest(path.read_bytes()) for path in directory.iterdir()}


def semantic(records):
    excluded = {"pipeline_run_id", "transform_version", "source_file_sha256"}
    return [{key: value for key, value in row.items() if key not in excluded} for row in records]


def worker(pipeline, source, fixture_dir, output_dir):
    hosted_guard()
    attempts = []

    def guard(event, args):
        if event.startswith("socket.") or event in {
            "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn",
            "os.spawn", "os.fork", "os.forkpty", "pty.spawn",
        }:
            attempts.append(event)
            raise InfrastructureFailure("network/process launch is forbidden: " + event)

    sys.addaudithook(guard)
    need(sys.flags.isolated, "worker needs -I isolation")
    source = Path(source).resolve()
    fixture_dir = Path(fixture_dir).resolve()
    output_dir = Path(output_dir).resolve()
    need(not output_dir.is_relative_to(source) and not fixture_dir.is_relative_to(source), "fixture/output inside source")
    output_dir.mkdir()
    os.chdir(output_dir)
    if pipeline == "AWS":
        sys.path.insert(0, str(source / "aws-market-data-pipeline"))
        module = importlib.import_module("function.processor")
        app = importlib.import_module("function.app")
        need(module.SYMBOL_ALIASES == ALIASES, "AWS alias mapping differs from exact fixture")
    else:
        need(pipeline == "local", "unknown pipeline")
        sys.path.insert(0, str(source / "market-data-pipeline-sample" / "src"))
        module = importlib.import_module("hydra_market_pipeline.pipeline")
        writers = importlib.import_module("hydra_market_pipeline.writers")
    results = {}
    for variant in ("unpadded", "padded"):
        repeated = []
        for repetition in range(2):
            path = output_dir / (variant + "-" + str(repetition))
            path.mkdir()
            source_bytes = (fixture_dir / (variant + ".csv")).read_bytes()
            if pipeline == "AWS":
                batch = module.process_csv(source_bytes)
                artifacts = dict(batch.artifacts)
                calls = []

                class RecordingS3:
                    def put_object(self, **kwargs):
                        calls.append(kwargs)

                returned_keys = app._write_batch(RecordingS3(), "fixture-curated", batch)
                need(len(calls) == 3 and returned_keys == [call["Key"] for call in calls], "unexpected writer calls")
                artifact_order = ("normalized_events.jsonl", "quarantine_records.jsonl", "manifest.json")
                prefixes = ("accepted", "quarantine", "manifests")
                for name, prefix, call in zip(artifact_order, prefixes, calls, strict=True):
                    need(set(call) == {"Body", "Bucket", "ContentType", "Key", "Metadata", "ServerSideEncryption"}, "writer call shape")
                    need(call["Body"] == artifacts[name] and call["Bucket"] == "fixture-curated"
                         and call["Key"] == "curated/" + prefix + "/" + batch.run_id + "/" + name
                         and call["ServerSideEncryption"] == "AES256", "actual writer bytes/keys mismatch")
                    need(call["ContentType"] == ("application/json" if name == "manifest.json" else "application/x-ndjson"), "writer content type mismatch")
                    need(call["Metadata"] == {"pipeline-run-id": batch.run_id,
                         "source-sha256": batch.source_file_sha256,
                         "transform-version": module.TRANSFORM_VERSION.replace("/", "-")}, "writer transform metadata mismatch")
                accepted, quarantined = list(batch.accepted), list(batch.quarantined)
                run_id, source_hash = batch.run_id, batch.source_file_sha256
                alias_hash = object_digest(module.SYMBOL_ALIASES)
                writer_metadata = calls[0]["Metadata"]
                keys = returned_keys
                run_schema = None
            else:
                batch = module.run_pipeline(input_csv=fixture_dir / (variant + ".csv"), aliases_path=fixture_dir / "aliases.json")
                paths = writers.write_outputs(batch, output_dir=path)
                artifacts = {item.name: item.read_bytes() for item in paths.values()}
                need(dict(batch.resolved_aliases) == ALIASES, "local resolved aliases differ")
                need(artifacts["source_snapshot.csv"] == source_bytes and artifacts["resolved_symbol_aliases.json"] == canonical(ALIASES), "local input artifact changed")
                accepted = [item.json_record() for item in batch.accepted]
                quarantined = [item.json_record() for item in batch.quarantined]
                run_id, source_hash, alias_hash = batch.pipeline_run_id, batch.source_file_sha256, batch.aliases_sha256
                writer_metadata, keys, run_schema = None, None, module.RUN_SCHEMA
            manifest = json.loads(artifacts["manifest.json"])
            need(manifest["pipeline_run_id"] == run_id and manifest["transform_version"] == module.TRANSFORM_VERSION
                 and manifest["source_file_sha256"] == source_hash and manifest["aliases_sha256"] == alias_hash,
                 "manifest identity mismatch")
            need(manifest["accepted_rows"] == len(accepted) and manifest["quarantined_rows"] == len(quarantined), "manifest row totals mismatch")
            need(artifacts["normalized_events.jsonl"] == b"".join(canonical(row) + b"\n" for row in accepted), "accepted output byte mismatch")
            need(artifacts["quarantine_records.jsonl"] == b"".join(canonical(row) + b"\n" for row in quarantined), "quarantine output byte mismatch")
            for key, description in manifest["outputs"].items():
                artifact_name = key if pipeline == "AWS" else description["file"]
                need(description["sha256"] == digest(artifacts[artifact_name]), "manifest output hash mismatch")
            if pipeline == "local":
                for description in manifest["inputs"].values():
                    need(description["sha256"] == digest(artifacts[description["file"]]), "manifest input hash mismatch")
            repeated.append({"version": module.TRANSFORM_VERSION, "run_schema": run_schema, "run_id": run_id,
                             "source_sha256": source_hash, "aliases_sha256": alias_hash,
                             "accepted": accepted, "quarantined": quarantined, "manifest": manifest,
                             "artifacts": {name: value.decode("utf-8") for name, value in artifacts.items()},
                             "artifact_sha256": {name: digest(value) for name, value in artifacts.items()},
                             "writer_metadata": writer_metadata, "writer_keys": keys})
        need(repeated[0] == repeated[1], "identical replay changed output bytes or identities")
        results[variant] = repeated[0]
    imported = {}
    for name, value in sorted(sys.modules.items()):
        if name == "function" or name.startswith("function.") or name == "hydra_market_pipeline" or name.startswith("hydra_market_pipeline."):
            file = Path(value.__file__).resolve()
            need(file.is_relative_to(source), "production import escaped assigned source checkout")
            imported[str(file.relative_to(source))] = digest(file.read_bytes())
    need(not attempts, "network/process operation attempted")
    print(json.dumps({"pipeline": pipeline, "results": results, "imported_sources": imported,
                      "network_attempts": 0, "process_launch_attempts": 0,
                      "repeat_exact": True}, sort_keys=True), flush=True)


def validate_result(pipeline, revision, variant, result, fixture_hashes):
    need(result["source_sha256"] == fixture_hashes[variant + ".csv"], "source digest mismatch")
    need(result["aliases_sha256"] == object_digest(ALIASES), "alias digest mismatch")
    identity = {"aliases_sha256": result["aliases_sha256"], "source_file_sha256": result["source_sha256"],
                "transform_version": result["version"]}
    if pipeline == "local":
        identity["run_schema"] = result["run_schema"]
    need(result["run_id"] == object_digest(identity), "run ID does not bind returned identity fields")
    if revision == "baseline":
        need(result["version"] == ("hydra-aws-market-normalizer/v1" if pipeline == "AWS" else "hydra-market-normalizer/v1"), "baseline version changed")
    if revision == "baseline" and variant == "padded":
        need(result["accepted"] == [] and len(result["quarantined"]) == 1, "baseline padded semantic prerequisite failed")
        record = result["quarantined"][0]
        empty = {name: "" for name in COLUMNS}
        need(record["raw_record"] == empty and record["errors"] == MISSING_ERRORS
             and record["raw_record_sha256"] == object_digest(empty) and record["source_row_number"] == 2,
             "baseline did not exhibit the exact missing canonical fields")
        need(record["quarantine_id"] == object_digest({"errors": MISSING_ERRORS,
             "raw_record_sha256": object_digest(empty), "source_row_number": 2}), "baseline quarantine identity mismatch")
        return
    need(result["quarantined"] == [] and len(result["accepted"]) == 1, "successful fixture prerequisite failed")
    raw = dict(zip(COLUMNS, VALUES, strict=True))
    expected = {"currency": "USD", "event_id": object_digest({"event_time_utc": "2026-10-09T12:00:00.000000Z", "symbol": "AAA", "venue": "XNAS"}),
                "event_time_utc": "2026-10-09T12:00:00.000000Z", "price": "1.250000",
                "raw_record_sha256": object_digest(raw), "source_file_sha256": result["source_sha256"],
                "source_record_id": "fixture-1", "source_row_number": 2, "source_system": "SYNTH_A",
                "symbol": "AAA", "transform_version": result["version"], "venue": "XNAS", "volume": 10}
    if pipeline == "AWS":
        expected["pipeline_run_id"] = result["run_id"]
    need(result["accepted"] == [expected], "normalized record does not exactly match valid fixture")


def main():
    hosted_guard()
    current = Path(__file__).resolve().parents[1]
    baseline = Path(sys.argv[1]).resolve()
    need(not current.is_relative_to(baseline) and not baseline.is_relative_to(current), "source checkouts must be siblings")
    sources = {"baseline": baseline, "current": current}
    before = {label: inventory(root) for label, root in sources.items()}
    need(before["baseline"]["head"] == BASE_HEAD and before["baseline"]["tree"] == BASE_TREE, "historical checkout is not exact baseline")
    need(before["current"]["head"] == os.environ["EXPECTED_HEAD"], "candidate is not exact requested PR head")
    rows = []
    try:
        with tempfile.TemporaryDirectory(prefix="r38-csv-", dir=os.environ["RUNNER_TEMP"]) as raw:
            temp = Path(raw).resolve()
            need(all(not temp.is_relative_to(root) for root in sources.values()), "temporary area inside source")
            fixture_dir = temp / "fixtures"
            fixture_dir.mkdir()
            fixture_hashes = fixtures(fixture_dir)
            observations = {}
            for pipeline in ("AWS", "local"):
                for revision, source in sources.items():
                    destination = temp / (pipeline + "-" + revision)
                    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker", pipeline,
                               str(source), str(fixture_dir), str(destination)]
                    completed = subprocess.run(command, cwd=temp, capture_output=True, text=True, timeout=60)
                    need(completed.returncode == 0 and not completed.stderr, "worker failure: " + revision + "/" + pipeline + ": " + completed.stderr)
                    output = json.loads(completed.stdout)
                    need(output["network_attempts"] == 0 and output["process_launch_attempts"] == 0
                         and output["repeat_exact"], "worker guard/replay failure")
                    for path, value in output["imported_sources"].items():
                        need(before[revision]["files"].get(path) == value, "imported source was not exact tracked bytes")
                    observations[(pipeline, revision)] = output
                    for variant, result in output["results"].items():
                        validate_result(pipeline, revision, variant, result, fixture_hashes)
                    print(json.dumps({"observation": revision + "/" + pipeline, **output}, sort_keys=True), flush=True)
            need({path.name: digest(path.read_bytes()) for path in fixture_dir.iterdir()} == fixture_hashes, "fixture bytes changed")
            for pipeline in ("AWS", "local"):
                old = observations[(pipeline, "baseline")]["results"]
                new = observations[(pipeline, "current")]["results"]
                need(semantic(old["unpadded"]["accepted"]) == semantic(new["unpadded"]["accepted"])
                     == semantic(new["padded"]["accepted"]), "ordinary/header-corrected semantic records differ")
                rows.append({"case": pipeline + "_unpadded_success_control", "result": "PASS",
                             "mechanism": "exact_expected_record_shape_raw_hash_and_replay_bytes",
                             "baseline_version": old["unpadded"]["version"], "candidate_version": new["unpadded"]["version"]})
                left, right = old["padded"], new["padded"]
                need(left["source_sha256"] == right["source_sha256"] and left["aliases_sha256"] == right["aliases_sha256"], "cross-revision input identity mismatch")
                business_changed = (left["accepted"], left["quarantined"]) != (right["accepted"], right["quarantined"])
                need(business_changed and len(left["accepted"]) == 0 and len(right["accepted"]) == 1, "no established business-output change")
                separated = left["run_id"] != right["run_id"]
                version_separated = left["version"] != right["version"]
                keys_separated = None if pipeline == "local" else not bool(set(left["writer_keys"]) & set(right["writer_keys"]))
                passed = separated and version_separated and keys_separated is not False
                mechanism = ("changed_outputs_same_run_id" if not separated else
                             "identity_separated_but_transform_version_or_keys_reused" if not passed else
                             "changed_business_outputs_have_separate_version_and_run_namespace")
                rows.append({"case": pipeline + "_same_padded_input_identity", "result": "PASS" if passed else "FAIL",
                             "mechanism": mechanism, "source_sha256": left["source_sha256"], "aliases_sha256": left["aliases_sha256"],
                             "baseline_run_id": left["run_id"], "candidate_run_id": right["run_id"],
                             "business_outputs_changed": business_changed, "run_ids_separated": separated,
                             "transform_versions_separated": version_separated, "AWS_keys_separated": keys_separated})
    except BaseException as exc:
        rows.append({"case": "proof_infrastructure", "result": "INFRASTRUCTURE_FAIL", "error": repr(exc)})
    finally:
        for revision, source in sources.items():
            after = inventory(source)
            need(before[revision] == after, "source identity or tracked bytes changed: " + revision)
            print(json.dumps({"source": revision, "head": after["head"], "tree": after["tree"],
                              "tracked_files": len(after["files"]), "source_unchanged": True}), flush=True)
    for row in rows:
        print(json.dumps(row, sort_keys=True), flush=True)
    totals = {"cases": len(rows), "passed": sum(row["result"] == "PASS" for row in rows),
              "failed": sum(row["result"] == "FAIL" for row in rows),
              "infrastructure_failures": sum(row["result"] == "INFRASTRUCTURE_FAIL" for row in rows)}
    print(json.dumps(totals, sort_keys=True), flush=True)
    return 0 if totals == {"cases": 4, "passed": 4, "failed": 0, "infrastructure_failures": 0} else 1


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--worker":
        worker(*sys.argv[2:])
    else:
        raise SystemExit(main())
