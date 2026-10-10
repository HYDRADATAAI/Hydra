from __future__ import annotations

import json
import sqlite3
import unittest

from run_demo import BUILD, SQL_FILES, build_database


class SqlDataQualitySampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = build_database()

    def connection(self):
        return sqlite3.connect(self.db)

    @staticmethod
    def synthetic_quality_connection():
        con = sqlite3.connect(":memory:")
        for sql_file in SQL_FILES:
            con.executescript(sql_file.read_text(encoding="utf-8"))
        con.executemany(
            """
            INSERT INTO raw_market_events(
                source_system, source_record_id, symbol, event_time_utc,
                price, volume, currency, venue
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("SYNTH", "bad-month", "AAA", "2026-99-99T99:99:99Z", 10.0, 1, "USD", "XNAS"),
                ("SYNTH", "bad-calendar-day", "BBB", "2026-02-30T12:00:00Z", 10.0, 1, "USD", "XNYS"),
                ("SYNTH", "valid-leap-day", "CCC", "2024-02-29T12:00:00Z", 10.0, 1, "USD", "XNAS"),
                ("SYNTH", "text-price", "FFF", "2026-09-24T17:30:00Z", "not-a-price", 1, "USD", "XNAS"),
                ("SYNTH", "blob-price", "GGG", "2026-09-24T17:30:00Z", b"not-a-price", 1, "USD", "XNYS"),
                ("SYNTH", "positive-infinity", "DDD", "2026-09-24T17:30:00Z", float("inf"), 1, "USD", "XNAS"),
                ("SYNTH", "negative-infinity", "HHH", "2026-09-24T17:30:00Z", float("-inf"), 1, "USD", "XNYS"),
                ("SYNTH", "large-finite", "EEE", "2026-09-24T17:30:00Z", 1e300, 1, "USD", "XNYS"),
            ],
        )
        return con

    def test_timestamps_must_round_trip_as_real_utc_calendar_times(self):
        con = self.synthetic_quality_connection()
        try:
            issues = dict(con.execute(
                """
                SELECT r.source_record_id, q.quality_issue
                FROM raw_market_events r
                JOIN quality_flags q USING (row_id)
                """
            ).fetchall())
        finally:
            con.close()
        self.assertEqual(issues["bad-month"], "invalid_timestamp")
        self.assertEqual(issues["bad-calendar-day"], "invalid_timestamp")
        self.assertIsNone(issues["valid-leap-day"])

    def test_invalid_price_types_and_infinities_are_quarantined(self):
        con = self.synthetic_quality_connection()
        try:
            issues = dict(con.execute(
                """
                SELECT r.source_record_id, q.quality_issue
                FROM raw_market_events r
                JOIN quality_flags q USING (row_id)
                """
            ).fetchall())
            accepted = {
                row[0] for row in con.execute(
                    """
                    SELECT r.source_record_id
                    FROM accepted_events e
                    JOIN raw_market_events r USING (row_id)
                    """
                ).fetchall()
            }
        finally:
            con.close()
        self.assertEqual(issues["text-price"], "invalid_price_type")
        self.assertEqual(issues["blob-price"], "invalid_price_type")
        self.assertEqual(issues["positive-infinity"], "non_finite_price")
        self.assertEqual(issues["negative-infinity"], "non_finite_price")
        self.assertIsNone(issues["large-finite"])
        self.assertNotIn("text-price", accepted)
        self.assertNotIn("blob-price", accepted)
        self.assertNotIn("positive-infinity", accepted)
        self.assertNotIn("negative-infinity", accepted)
        self.assertIn("large-finite", accepted)

    def test_expected_accept_and_quarantine_counts(self):
        con = self.connection()
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM accepted_events").fetchone()[0], 5)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM quarantine_events").fetchone()[0], 3)
        finally:
            con.close()

    def test_quality_reasons_are_explicit(self):
        con = self.connection()
        try:
            reasons = dict(con.execute(
                "SELECT quality_issue, COUNT(*) FROM quarantine_events GROUP BY quality_issue"
            ).fetchall())
        finally:
            con.close()
        self.assertEqual(reasons, {
            "duplicate_normalized_event": 1,
            "invalid_timestamp": 1,
            "non_positive_price": 1,
        })

    def test_alias_join_collapses_duplicate_identity(self):
        con = self.connection()
        try:
            rows = con.execute(
                "SELECT row_id, symbol, event_key FROM normalized_events "
                "WHERE source_record_id IN ('a-001','b-777') ORDER BY row_id"
            ).fetchall()
        finally:
            con.close()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][1], "AAA")
        self.assertEqual(rows[1][1], "AAA")
        self.assertEqual(rows[0][2], rows[1][2])

    def test_window_function_summary_for_bbb(self):
        con = self.connection()
        try:
            bbb = con.execute(
                "SELECT accepted_rows, total_volume, max_step_return_pct "
                "FROM symbol_activity_summary WHERE symbol='BBB'"
            ).fetchone()
        finally:
            con.close()
        self.assertEqual(bbb[0], 3)
        self.assertEqual(bbb[1], 3300)
        self.assertGreater(bbb[2], 1.9)

    def test_summary_file_matches_database(self):
        summary = json.loads((BUILD / "quality_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["accepted"], 5)
        self.assertEqual(summary["duplicate_normalized_event"], 1)


if __name__ == "__main__":
    unittest.main()
