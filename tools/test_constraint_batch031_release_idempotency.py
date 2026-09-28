from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "tools/materialize_constraint_second_slice_batch031_private_t1.py"
QUEUE = ROOT / "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
STORE_SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Batch031ReleaseIdempotencyTests(unittest.TestCase):
    def prepare(self, root: Path) -> tuple[Path, Path, dict]:
        private = root / "raw"
        inbox = root / "inbox"
        inbox.mkdir(parents=True)
        queue = load(QUEUE)
        stamp = "2026-09-28T20:00:00Z"
        for item in queue["queue"]:
            capture = inbox / item["inbox_filename"]
            body = (
                b"%PDF-1.7\n" + b"x" * 2048
                if item["content_type_hint"] == "application/pdf"
                else b"<!doctype html><html><body>fixture</body></html>"
            )
            capture.write_bytes(body)
            sidecar = {
                "schema_version": "hydra-semiconductor-private-capture-sidecar/v1",
                "capture_intent_id": item["capture_intent_id"],
                "source_id": item["source_id"],
                "source_version_id": item["source_version_id"],
                "source_locator": item["source_locator"],
                "capture_completed_at": stamp,
                "content_type": item["content_type_hint"],
                "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            }
            Path(str(capture) + ".capture.json").write_text(
                json.dumps(sidecar, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return private, inbox, queue

    def run_materializer(self, private: Path, inbox: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(MATERIALIZER),
                "--repo-root", str(ROOT),
                "--private-root", str(private),
                "--inbox-root", str(inbox),
            ],
            text=True,
            capture_output=True,
        )

    def test_second_run_reuses_exact_immutable_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            private, inbox, queue = self.prepare(Path(td))
            first = self.run_materializer(private, inbox)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("T1_RELEASE_REUSED=NO", first.stdout)
            release_path = private / "releases" / f"{queue['release_id']}.json"
            before = release_path.read_bytes()

            second = self.run_materializer(private, inbox)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("T1_RELEASE_REUSED=YES", second.stdout)
            self.assertEqual(release_path.read_bytes(), before)

    def test_existing_valid_release_with_wrong_membership_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            private, inbox, queue = self.prepare(Path(td))
            first = self.run_materializer(private, inbox)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            sys.path.insert(0, str(STORE_SRC))
            from hydra_constraint_t1_raw.store import build_release_manifest, _canonical_json

            receipts = []
            for item in queue["queue"][:-1]:
                rp = private / "receipts" / item["source_id"] / f"{item['source_version_id']}.json"
                receipts.append(load(rp))
            release = build_release_manifest(
                release_id=queue["release_id"],
                created_at="2026-09-28T20:01:00Z",
                receipts=receipts,
            )
            release_path = private / "releases" / f"{queue['release_id']}.json"
            release_path.write_bytes(_canonical_json(release))

            second = self.run_materializer(private, inbox)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn(
                "existing immutable release membership differs from Batch031 receipts",
                second.stdout + second.stderr,
            )


if __name__ == "__main__":
    unittest.main()
