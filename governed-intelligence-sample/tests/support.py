from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parent
PIPELINE = REPOSITORY / "market-data-pipeline-sample"
sys.path.insert(0, str(PIPELINE / "src"))

from hydra_market_pipeline import run_pipeline, write_outputs  # noqa: E402


def build_pipeline_outputs(output_dir: Path) -> Path:
    result = run_pipeline(
        input_csv=PIPELINE / "data/raw/synthetic_market_events.csv",
        aliases_path=PIPELINE / "config/symbol_aliases.json",
    )
    write_outputs(result, output_dir=output_dir)
    return output_dir


def build_pipeline_outputs_from_rows(
    output_dir: Path,
    *,
    rows: list[Mapping[str, str]],
    aliases: Mapping[str, str],
) -> Path:
    input_dir = output_dir.parent / f"{output_dir.name}-inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    source_path = input_dir / "source.csv"
    aliases_path = input_dir / "aliases.json"

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=(
            "source_system",
            "source_record_id",
            "symbol",
            "event_time",
            "price",
            "volume",
            "currency",
            "venue",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    source_path.write_bytes(buffer.getvalue().encode("utf-8"))
    aliases_path.write_text(
        json.dumps(dict(aliases), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_pipeline(input_csv=source_path, aliases_path=aliases_path)
    write_outputs(result, output_dir=output_dir)
    return output_dir
