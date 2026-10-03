"""Windows-only canary aggregate boundary probes using synthetic responses.

Run with: python -B canary_boundary_probe.py --repo D:\\path\\to\\candidate
No network transport is constructed; candidate source files are never written.
This external review probe does not change any PR's source or test bytes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest


class CanaryAggregateBoundaryTests(unittest.TestCase):
    def assert_inert(self, report):
        self.assertIs(report["read_only"], True)
        self.assertIs(report["ledger_mutation"], False)
        self.assertIs(report["automatic_trading_action"], False)
        self.assertEqual(report["status_scope"], "CURRENT_FETCH_AND_MARKERS_ONLY")
        admission = report["admission"]
        self.assertEqual(admission["status"], "BLOCKED")
        self.assertIs(admission["canonical_admission"], False)
        self.assertIs(admission["readiness_promotion"], False)
        gates = admission["gates"]
        self.assertEqual(gates["D_OWNER_GATE"], "BLOCKED")
        self.assertEqual(gates["IMPLEMENTATION_ADMITTED"], "NO")
        self.assertEqual(gates["PIT_002B"], "OPEN")
        self.assertEqual(gates["EATON_TIMESTAMP"], "TIMESTAMP_UNVERIFIED")
        self.assertEqual(gates["GE_VERNOVA_TIMESTAMP"], "TIMESTAMP_UNVERIFIED")

    def spec(self, name, *, enabled=True):
        return CanarySpec(name, "https://example.invalid/" + name, ["marker"], enabled=enabled)

    def test_nonempty_all_disabled_report_is_failure_without_fetches(self):
        transport = ProbeTransport({})
        report = CanaryRunner(transport).run([
            self.spec("disabled-a", enabled=False),
            self.spec("disabled-b", enabled=False),
        ])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["enabled_sources"], 0)
        self.assertEqual(report["passed_sources"], 0)
        self.assertEqual(transport.calls, [])
        self.assertEqual([r["name"] for r in report["results"]], ["disabled-a", "disabled-b"])
        self.assertEqual([r["status"] for r in report["results"]], ["DISABLED", "DISABLED"])
        self.assertTrue(all(r["enabled"] is False for r in report["results"]))
        self.assertTrue(all(r["http_status"] is None and r["sha256"] is None
                            and r["bytes_read"] == 0 for r in report["results"]))
        self.assert_inert(report)

    def test_disabled_source_does_not_mask_enabled_failure(self):
        transport = ProbeTransport({
            "good": CanaryResponse(200, "https://example.invalid/good", {}, b"marker"),
            "bad": CanaryResponse(503, "https://example.invalid/bad", {}, b"marker"),
        })
        report = CanaryRunner(transport).run([
            self.spec("disabled", enabled=False), self.spec("good"), self.spec("bad"),
        ])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["enabled_sources"], 2)
        self.assertEqual(report["passed_sources"], 1)
        self.assertEqual(transport.calls, ["good", "bad"])
        self.assertEqual([r["status"] for r in report["results"]], ["DISABLED", "PASS", "FAIL"])
        self.assert_inert(report)

    def test_disabled_source_does_not_invalidate_real_enabled_success(self):
        transport = ProbeTransport({
            "good": CanaryResponse(200, "https://example.invalid/good", {}, b"marker"),
        })
        report = CanaryRunner(transport).run([
            self.spec("disabled", enabled=False), self.spec("good"),
        ])
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["enabled_sources"], 1)
        self.assertEqual(report["passed_sources"], 1)
        self.assertEqual(transport.calls, ["good"])
        self.assertEqual([r["status"] for r in report["results"]], ["DISABLED", "PASS"])
        self.assert_inert(report)


class ProbeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def fetch(self, spec, user_agent):
        self.calls.append(spec.name)
        if spec.name not in self.responses:
            raise AssertionError("Unexpected fetch: " + spec.name)
        return self.responses[spec.name]


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows required; this probe must not import HYDRA on Linux")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if repo.drive.upper() != "D:":
        raise SystemExit("A D: candidate checkout is required")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo / "constraint-runtime" / "src"))
    global CanaryResponse, CanaryRunner, CanarySpec
    from hydra_constraint.canary import CanaryResponse, CanaryRunner, CanarySpec
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CanaryAggregateBoundaryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped or result.testsRun != 3:
        raise SystemExit("All three aggregate probes must execute without skips")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

