from __future__ import annotations

import json
import sqlite3
import unittest

from run_demo import BUILD, build_database

class SqlDataQualitySampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = build_database()

    def connection(self):
        return sqlite3.connect(self.db)

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
