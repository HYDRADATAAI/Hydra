from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(STORE_SRC))

from hydra_constraint_t1_raw.store import RawArtifactStore  # noqa: E402

MATERIALIZER = ROOT / "tools" / "materialize_constraint_second_slice_batch031_private_t1.py"
SPEC = importlib.util.spec_from_file_location("batch031_materializer_idempotency", MATERIALIZER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch031 materializer")
materializer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(materializer)


class Batch031ReleaseIdempotencyTests(unittest.TestCase):
    def receipt(
        self,
        store: RawArtifactStore,
        *,
        source_id: str,
        source_version_id: str,
        payload: bytes,
    ) -> dict:
        ts = "2026-09-28T21:30:00+00:00"
        return store.persist(
            raw_bytes=payload,
            source_id=source_id,
            source_version_id=source_version_id,
            content_type="text/html",
            acquired_at=ts,
            available_at=ts,
            source_locator=f"https://example.test/{source_id}",
            processing_disposition="ELIGIBLE",
        )

    def test_second_materialization_reuses_exact_immutable_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private"
            store = RawArtifactStore(root=private)
            receipts = [
                self.receipt(
                    store,
                    source_id="SRC-TEST-001",
                    source_version_id="SV-TEST-001",
                    payload=b"<html>one</html>",
                ),
                self.receipt(
                    store,
                    source_id="SRC-TEST-002",
                    source_version_id="SV-TEST-002",
                    payload=b"<html>two</html>",
                ),
            ]

            first, reused_first = materializer.materialize_or_reuse_release(
                store=store,
                private=private,
                release_id="REL-TEST-B031",
                receipts=receipts,
            )
            release_path = private / "releases" / "REL-TEST-B031.json"
            first_bytes = release_path.read_bytes()

            second, reused_second = materializer.materialize_or_reuse_release(
                store=store,
                private=private,
                release_id="REL-TEST-B031",
                receipts=receipts,
            )

            self.assertFalse(reused_first)
            self.assertTrue(reused_second)
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, release_path.read_bytes())
            self.assertEqual((), store.validate_stored_release_manifest(second))

    def test_existing_release_rejects_changed_receipt_set(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private"
            store = RawArtifactStore(root=private)
            r1 = self.receipt(
                store,
                source_id="SRC-TEST-001",
                source_version_id="SV-TEST-001",
                payload=b"<html>one</html>",
            )
            r2 = self.receipt(
                store,
                source_id="SRC-TEST-002",
                source_version_id="SV-TEST-002",
                payload=b"<html>two</html>",
            )
            materializer.materialize_or_reuse_release(
                store=store,
                private=private,
                release_id="REL-TEST-B031",
                receipts=[r1, r2],
            )

            r3 = self.receipt(
                store,
                source_id="SRC-TEST-003",
                source_version_id="SV-TEST-003",
                payload=b"<html>three</html>",
            )
            with self.assertRaisesRegex(
                SystemExit,
                "existing immutable release does not match current 30-receipt set",
            ):
                materializer.materialize_or_reuse_release(
                    store=store,
                    private=private,
                    release_id="REL-TEST-B031",
                    receipts=[r1, r3],
                )


if __name__ == "__main__":
    unittest.main()
