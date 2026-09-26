from __future__ import annotations

import sys
from pathlib import Path


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
