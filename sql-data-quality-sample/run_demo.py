from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "synthetic_market_events.csv"
BUILD = ROOT / "build"
DB = BUILD / "hydra_sql_demo.db"

SQL_FILES = [
    ROOT / "sql" / "01_schema.sql",
    ROOT / "sql" / "02_quality.sql",
    ROOT / "sql" / "03_analytics.sql",
]

def build_database() -> Path:
    BUILD.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()

    connection = sqlite3.connect(DB)
    try:
        for sql_file in SQL_FILES:
            connection.executescript(sql_file.read_text(encoding="utf-8"))

        with FIXTURE.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        connection.executemany(
            """
            INSERT INTO raw_market_events(
                source_system, source_record_id, symbol, event_time_utc,
                price, volume, currency, venue
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["source_system"],
                    row["source_record_id"],
                    row["symbol"],
                    row["event_time_utc"],
                    float(row["price"]),
                    int(row["volume"]),
                    row["currency"],
                    row["venue"],
                )
                for row in rows
            ],
        )
        connection.commit()

        summary = dict(
            connection.execute(
                "SELECT outcome, row_count FROM quality_summary ORDER BY outcome"
            ).fetchall()
        )
        (BUILD / "quality_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        connection.close()

    return DB

def main() -> None:
    db = build_database()
    connection = sqlite3.connect(db)
    try:
        accepted = connection.execute("SELECT COUNT(*) FROM accepted_events").fetchone()[0]
        quarantined = connection.execute("SELECT COUNT(*) FROM quarantine_events").fetchone()[0]
        symbols = connection.execute(
            "SELECT symbol, accepted_rows, total_volume, max_step_return_pct "
            "FROM symbol_activity_summary ORDER BY symbol"
        ).fetchall()
    finally:
        connection.close()

    print(f"SQL_SAMPLE_DB={db}")
    print(f"ACCEPTED_ROWS={accepted}")
    print(f"QUARANTINED_ROWS={quarantined}")
    print(f"SYMBOL_SUMMARY={symbols}")

if __name__ == "__main__":
    main()
