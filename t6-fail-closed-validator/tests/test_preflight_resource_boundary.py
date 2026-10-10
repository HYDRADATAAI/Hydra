"""Hosted-only focused regressions; do not execute on the local Linux host."""
from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from hydra_t6_failclosed import documents


class PreflightResourceBoundaryTests(unittest.TestCase):
    def assert_preflight_rejects(self, payload: str) -> None:
        raw = payload.encode("utf-8")
        with patch.object(documents.json, "loads", side_effect=AssertionError("json.loads reached before node rejection")) as loader:
            result = documents.parse_json_document(raw, label="$.document")
        loader.assert_not_called()
        self.assertIsNone(result.value)
        self.assertEqual([issue.code for issue in result.issues], ["document_too_large"])
        self.assertIn(
            result.issues[0].evidence,
            (
                {"node_count": documents.MAX_DOCUMENT_NODES + 1},
                {"normalization_limit": "nodes"},
            ),
        )
        self.assertEqual(result.raw, raw)
        self.assertEqual(result.raw_sha256, hashlib.sha256(raw).hexdigest())

    def numeric_payload(self) -> str:
        return '{"items":[' + ','.join('0' for _ in range(documents.MAX_DOCUMENT_NODES)) + ']}'

    def test_lf_prefix_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects('\n' + self.numeric_payload())

    def test_tab_prefix_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects('\t' + self.numeric_payload())

    def test_cr_prefix_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects('\r' + self.numeric_payload())

    def test_true_prefix_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects('{"flag":true,"items":[' + ','.join('0' for _ in range(documents.MAX_DOCUMENT_NODES)) + ']}')

    def test_null_prefix_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects('{"flag":null,"items":[' + ','.join('0' for _ in range(documents.MAX_DOCUMENT_NODES)) + ']}')

    def test_numeric_control_rejected_before_parse(self) -> None:
        self.assert_preflight_rejects(self.numeric_payload())


if __name__ == '__main__':
    unittest.main()
