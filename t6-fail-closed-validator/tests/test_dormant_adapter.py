from __future__ import annotations

import unittest
from types import SimpleNamespace

from hydra_t6_failclosed.dormant_adapter import DormantValidationAdapter


class DormantValidationAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        # The adapter never invokes the validator while execution is dormant,
        # so a simple sentinel is sufficient for this boundary test.
        self.adapter = DormantValidationAdapter(validator=object())  # type: ignore[arg-type]

    def test_prepare_requires_explicit_dormant_readiness(self) -> None:
        with self.assertRaises(PermissionError):
            self.adapter.prepare(SimpleNamespace(readiness="active"))

    def test_prepare_accepts_dormant_readiness(self) -> None:
        self.adapter.prepare(SimpleNamespace(readiness="dormant"))

    def test_execute_always_refuses_runtime_effects(self) -> None:
        result = self.adapter.execute(
            SimpleNamespace(readiness="dormant"),
            {"candidate_id": "candidate-001"},
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.output, {})
        self.assertIn("not authorized", result.error or "")


if __name__ == "__main__":
    unittest.main()
