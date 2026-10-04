"""Synthetic regressions for the nullable outcome-mapping input boundary."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest

from hydra_constraint_replay.outcome_mapping import (
    OutcomeMappingError,
    OutcomeMappingInputs,
    POSITIVE_CONSTRAINT_RULESET_V1,
    load_outcome_mapping_bundle,
    map_positive_constraint_outcome,
)


INVALID_NULLABLE_BOOLEANS = (
    ("string_false", "false"),
    ("string_true", "true"),
    ("integer_zero", 0),
    ("integer_one", 1),
    ("float_zero", 0.0),
    ("float_one", 1.0),
    ("empty_list", []),
    ("empty_object", {}),
)


def synthetic_mapping(**changes):
    record = OutcomeMappingInputs(
        case_id="synthetic-nullable-mapping-contract",
        rule_set_id=POSITIVE_CONSTRAINT_RULESET_V1,
        mechanism_observed=True,
        direction_consistent=True,
        explicit_numeric_target_defined=True,
        target_met=True,
        explicit_horizon_defined=True,
        horizon_met=True,
        causal_attribution_clean=True,
        outcome_observation_complete=True,
        contradiction_open=False,
        evidence_source_ids=("synthetic-contract-source",),
        rationale="Synthetic typed-input regression only; not historical evidence.",
    )
    return replace(record, **changes)


def load_synthetic_mapping(record):
    case = asdict(record)
    case.pop("rule_set_id")
    bundle = {
        "schema_version": "1.0",
        "rule_set_id": POSITIVE_CONSTRAINT_RULESET_V1,
        "declared_at": "2000-01-01T00:00:00Z",
        "cases": [case],
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic-mapping.json"
        path.write_text(json.dumps(bundle, allow_nan=False), encoding="utf-8")
        _, records = load_outcome_mapping_bundle(path)
    return records[0]


class OutcomeMappingTypedInputTests(unittest.TestCase):
    def assert_rejected(self, record, route, field, value_name):
        try:
            if route == "json_loader":
                loaded = load_synthetic_mapping(record)
            else:
                decision = map_positive_constraint_outcome(record)
        except OutcomeMappingError:
            return

        if route == "json_loader":
            self.fail(
                f"JSON loader accepted {field}={value_name}; "
                f"returned value {getattr(loaded, field)!r} with type "
                f"{type(getattr(loaded, field)).__name__}"
            )
        self.fail(
            f"Direct mapping accepted {field}={value_name}; "
            f"produced {decision.outcome_class} instead of rejecting the input"
        )

    def outcome_for_route(self, record, route):
        if route == "json_loader":
            record = load_synthetic_mapping(record)
        return map_positive_constraint_outcome(record).outcome_class

    def test_direct_mapping_rejects_nonboolean_target_results(self):
        for name, value in INVALID_NULLABLE_BOOLEANS:
            with self.subTest(value=name):
                self.assert_rejected(
                    synthetic_mapping(target_met=value), "direct", "target_met", name
                )

    def test_direct_mapping_rejects_nonboolean_horizon_results(self):
        for name, value in INVALID_NULLABLE_BOOLEANS:
            with self.subTest(value=name):
                self.assert_rejected(
                    synthetic_mapping(horizon_met=value), "direct", "horizon_met", name
                )

    def test_json_loader_rejects_nonboolean_target_results(self):
        for name, value in INVALID_NULLABLE_BOOLEANS:
            with self.subTest(value=name):
                self.assert_rejected(
                    synthetic_mapping(target_met=value), "json_loader", "target_met", name
                )

    def test_json_loader_rejects_nonboolean_horizon_results(self):
        for name, value in INVALID_NULLABLE_BOOLEANS:
            with self.subTest(value=name):
                self.assert_rejected(
                    synthetic_mapping(horizon_met=value), "json_loader", "horizon_met", name
                )

    def test_boolean_results_preserve_complete_window_classification(self):
        expected = (
            (True, True, "TRUE_POSITIVE"),
            (False, True, "PARTIAL_REALIZATION"),
            (True, False, "RIGHT_MECHANISM_WRONG_TIMING"),
            (False, False, "RIGHT_MECHANISM_WRONG_TIMING"),
        )
        for route in ("direct", "json_loader"):
            for target, horizon, outcome in expected:
                with self.subTest(route=route, target=target, horizon=horizon):
                    record = synthetic_mapping(target_met=target, horizon_met=horizon)
                    self.assertEqual(outcome, self.outcome_for_route(record, route))

    def test_absent_target_and_horizon_preserve_null_results(self):
        record = synthetic_mapping(
            explicit_numeric_target_defined=False,
            target_met=None,
            explicit_horizon_defined=False,
            horizon_met=None,
        )
        for route in ("direct", "json_loader"):
            with self.subTest(route=route):
                self.assertEqual("PARTIAL_REALIZATION", self.outcome_for_route(record, route))

    def test_incomplete_explicit_horizon_accepts_null_and_remains_unevaluable(self):
        for route in ("direct", "json_loader"):
            for has_target in (False, True):
                with self.subTest(route=route, has_target=has_target):
                    record = synthetic_mapping(
                        explicit_numeric_target_defined=has_target,
                        target_met=True if has_target else None,
                        horizon_met=None,
                        outcome_observation_complete=False,
                    )
                    self.assertEqual("UNEVALUABLE", self.outcome_for_route(record, route))

    def test_defined_target_still_requires_nonnull_result(self):
        record = synthetic_mapping(target_met=None)
        for route in ("direct", "json_loader"):
            with self.subTest(route=route):
                with self.assertRaisesRegex(OutcomeMappingError, "target_met required"):
                    self.outcome_for_route(record, route)

    def test_complete_explicit_horizon_still_requires_nonnull_result(self):
        record = synthetic_mapping(horizon_met=None)
        for route in ("direct", "json_loader"):
            with self.subTest(route=route):
                with self.assertRaisesRegex(OutcomeMappingError, "horizon_met required"):
                    self.outcome_for_route(record, route)

    def test_undefined_target_or_horizon_still_forbids_nonnull_result(self):
        cases = (
            ("target_met", synthetic_mapping(explicit_numeric_target_defined=False)),
            ("horizon_met", synthetic_mapping(explicit_horizon_defined=False)),
        )
        for route in ("direct", "json_loader"):
            for field, record in cases:
                with self.subTest(route=route, field=field):
                    with self.assertRaisesRegex(OutcomeMappingError, f"{field} forbidden"):
                        self.outcome_for_route(record, route)


if __name__ == "__main__":
    unittest.main()
