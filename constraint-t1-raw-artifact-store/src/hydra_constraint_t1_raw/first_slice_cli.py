"""Materialize one complete reviewed first-slice source set into private T1 custody."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .first_slice_materialization import FirstSliceMaterializationError, materialize_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--capture-plan", required=True)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--public-repo-root", required=True)
    parser.add_argument("--attestation-output")
    args = parser.parse_args()

    try:
        attestation = materialize_files(
            registry_path=args.registry,
            plan_path=args.capture_plan,
            private_root=args.private_root,
            public_repo_root=args.public_repo_root,
        )
    except FirstSliceMaterializationError as exc:
        print("FIRST_SLICE_PRIVATE_MATERIALIZATION=FAIL")
        print(f"ERROR={exc}")
        return 1

    encoded = json.dumps(attestation, indent=2, sort_keys=True)
    if args.attestation_output:
        output = Path(args.attestation_output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    print("FIRST_SLICE_PRIVATE_MATERIALIZATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
