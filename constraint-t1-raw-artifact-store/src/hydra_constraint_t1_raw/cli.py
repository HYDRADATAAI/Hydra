"""Persist one already-captured local file into a private HYDRA raw store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .store import RawArtifactStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--public-repo-root", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-version-id", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--source-locator", required=True)
    parser.add_argument("--acquired-at", required=True)
    parser.add_argument("--available-at", required=True)
    parser.add_argument("--disposition", default="ELIGIBLE", choices=["ELIGIBLE", "QUARANTINED", "INELIGIBLE"])
    args = parser.parse_args()

    store = RawArtifactStore(
        root=Path(args.private_root),
        public_repo_root=Path(args.public_repo_root),
    )
    receipt = store.persist(
        raw_bytes=Path(args.input_file).read_bytes(),
        source_id=args.source_id,
        source_version_id=args.source_version_id,
        content_type=args.content_type,
        acquired_at=args.acquired_at,
        available_at=args.available_at,
        source_locator=args.source_locator,
        processing_disposition=args.disposition,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
