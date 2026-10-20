from __future__ import annotations

import unittest

from hydra_governed_intelligence.pipeline_replay import replay_pipeline


class PipelineReplayTests(unittest.TestCase):
    def test_trimmed_headers_are_used_for_row_lookup(self) -> None:
        source = (
            b"source_system,source_record_id,symbol,event_time,price,volume,currency,venue\n"
            b"SYNTH_A,record-1,AAA,2026-10-09T12:00:00Z,1.25,10,USD,XNAS\n"
        )
        header, body = source.split(b"\n", 1)
        padded = b",".join(b" " + field + b" " for field in header.split(b","))
        aliases = b"{}"

        expected = replay_pipeline(source_bytes=source, aliases_bytes=aliases)
        actual = replay_pipeline(
            source_bytes=padded + b"\n" + body,
            aliases_bytes=aliases,
        )

        self.assertEqual(actual.source_rows, expected.source_rows)
        self.assertEqual(len(actual.accepted), 1)
        self.assertEqual(len(actual.quarantined), 0)
        self.assertEqual(actual.accepted[0]["event_id"], expected.accepted[0]["event_id"])
        self.assertEqual(actual.accepted[0]["raw_record_sha256"], expected.accepted[0]["raw_record_sha256"])
        for field in (
            "source_system",
            "source_record_id",
            "symbol",
            "event_time_utc",
            "price",
            "volume",
            "currency",
            "venue",
        ):
            self.assertEqual(actual.accepted[0][field], expected.accepted[0][field])


if __name__ == "__main__":
    unittest.main()
