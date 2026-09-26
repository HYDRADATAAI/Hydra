"""Verify recovered authority bytes; this does not validate runtime conformance."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "docs/constraint/authority/thread3_recovered_pass002_20260926"
PREFIX = "HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS002_THREAD3_"
ARCHIVE = AUTHORITY / (PREFIX + "ORIGINAL_CLOSURE_BUNDLE_20260926.zip")
EXPECTED = "ab7e4c05c9210a90256b8cdea89eeb9f3bb551453dfe13ebfe44616f750cb366"


def verify(path: Path = ARCHIVE) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError("Thread-3 master bundle digest mismatch")
    checked = []
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        manifest = json.loads(outer.read("MANIFEST.json"))
        for entry in manifest["contents"]:
            data = outer.read(entry["path"])
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("Outer member digest/size mismatch: " + entry["path"])
            checked.append(entry["path"])
            if entry["path"].endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as nested:
                    child_manifest = json.loads(nested.read("MANIFEST.json"))
                    for child in child_manifest["files"]:
                        content = nested.read(child["name"])
                        if len(content) != child["bytes"] or hashlib.sha256(content).hexdigest() != child["sha256"]:
                            raise ValueError("Nested member digest/size mismatch: " + child["name"])
                        checked.append(entry["path"] + "!" + child["name"])
        index_path = AUTHORITY / (PREFIX + "RECOVERED_MEMBER_INDEX_20260926.json")
        for row in json.loads(index_path.read_text())["readable_copies"]:
            with zipfile.ZipFile(io.BytesIO(outer.read(row["archive_member"]))) as nested:
                expected = nested.read(row["nested_member"])
            actual = (ROOT / row["repository_path"]).read_bytes()
            if actual != expected:
                raise ValueError("Readable authority copy differs: " + row["repository_path"])
    return {
        "authority_bytes": "PASS",
        "master_sha256": EXPECTED,
        "manifest_member_checks": len(checked),
        "runtime_conformance": "NOT_RUN",
        "semiconductor_admission": "BLOCKED",
    }


if __name__ == "__main__":
    try:
        result = verify(Path(sys.argv[1]) if len(sys.argv) > 1 else ARCHIVE)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"authority_bytes": "FAIL", "error": str(exc)}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
