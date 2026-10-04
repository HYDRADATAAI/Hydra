"""Synthetic typed-input contracts; these fixtures are not performance evidence."""

from datetime import datetime, timedelta, timezone

import pytest

from hydra_constraint_replay.metrics import evaluate_cases
from hydra_constraint_replay.models import Evidence, Hypothesis, Outcome, ReplayCase
from hydra_constraint_replay.replay import replay_case


REPLAY_T = datetime(2020, 1, 1, tzinfo=timezone.utc)
PUBLIC_ENTRYPOINTS = ("replay_case", "evaluate_cases")


def _synthetic_case(*, confidence=0.8, realized=True, outcome_class="TRUE_POSITIVE"):
    known_at = REPLAY_T - timedelta(days=1)
    return ReplayCase(
        case_id="synthetic-typed-input-contract",
        replay_t=REPLAY_T,
        hypothesis=Hypothesis(
            constraint_candidate="synthetic-constraint",
            confidence_at_t=confidence,
            expected_mechanism="synthetic-capacity-loss",
            expected_direction="tightening",
        ),
        evidence=[
            Evidence(
                evidence_id="synthetic-evidence",
                known_at=known_at,
                observed_at=known_at,
                source_uri="https://example.invalid/synthetic-typed-input-contract",
                source_hash="0" * 64,
                payload={"synthetic": True, "fact": "typed-input-contract"},
            )
        ],
        outcome=Outcome(
            outcome_class=outcome_class,
            realized_constraint=realized,
            impact_first_observed_at=None,
        ),
    )


def _invoke(entrypoint, case):
    if entrypoint == "replay_case":
        return replay_case(case)
    assert entrypoint == "evaluate_cases"
    return evaluate_cases([case])


@pytest.mark.parametrize("entrypoint", PUBLIC_ENTRYPOINTS)
@pytest.mark.parametrize("confidence", [True, False], ids=["bool-true", "bool-false"])
def test_public_entrypoints_reject_boolean_confidence(entrypoint, confidence):
    case = _synthetic_case(confidence=confidence)
    with pytest.raises(ValueError, match="confidence_at_t"):
        _invoke(entrypoint, case)


@pytest.mark.parametrize("entrypoint", PUBLIC_ENTRYPOINTS)
@pytest.mark.parametrize(
    "confidence",
    [
        pytest.param(-0.01, id="below-zero"),
        pytest.param(1.01, id="above-one"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="positive-infinity"),
        pytest.param(float("-inf"), id="negative-infinity"),
    ],
)
def test_existing_confidence_range_rejections_remain_closed(entrypoint, confidence):
    case = _synthetic_case(confidence=confidence)
    with pytest.raises(ValueError, match="confidence_at_t"):
        _invoke(entrypoint, case)


@pytest.mark.parametrize("entrypoint", PUBLIC_ENTRYPOINTS)
@pytest.mark.parametrize(
    "realized",
    [
        pytest.param(0, id="integer-zero"),
        pytest.param(1, id="integer-one"),
        pytest.param(2, id="integer-two"),
        pytest.param(-1, id="integer-negative"),
        pytest.param(0.0, id="float-zero"),
        pytest.param(1.0, id="float-one"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="positive-infinity"),
        pytest.param(float("-inf"), id="negative-infinity"),
        pytest.param("0", id="numeric-string-zero"),
        pytest.param("1", id="numeric-string-one"),
        pytest.param([], id="empty-list"),
        pytest.param([True], id="boolean-list"),
        pytest.param({}, id="empty-dict"),
        pytest.param({"value": True}, id="boolean-dict"),
        pytest.param((), id="empty-tuple"),
    ],
)
def test_public_entrypoints_reject_non_boolean_realized_target(entrypoint, realized):
    case = _synthetic_case(realized=realized)
    # Incidental float(container) TypeError is not a field-specific rejection.
    with pytest.raises(ValueError, match="realized_constraint"):
        _invoke(entrypoint, case)


@pytest.mark.parametrize(
    "confidence,realized,outcome_class",
    [
        pytest.param(0, False, "TRUE_NEGATIVE", id="integer-zero"),
        pytest.param(1, True, "TRUE_POSITIVE", id="integer-one"),
        pytest.param(0.0, False, "TRUE_NEGATIVE", id="float-zero"),
        pytest.param(1.0, True, "TRUE_POSITIVE", id="float-one"),
    ],
)
def test_numeric_confidence_endpoints_and_boolean_targets_remain_valid(
    confidence, realized, outcome_class
):
    case = _synthetic_case(
        confidence=confidence, realized=realized, outcome_class=outcome_class
    )
    row = replay_case(case)
    assert row["hypothesis"]["confidence_at_t"] == confidence
    assert type(row["hypothesis"]["confidence_at_t"]) is type(confidence)
    assert row["realized_constraint"] is realized
    metrics = evaluate_cases([case])
    assert metrics["case_count"] == 1
    assert metrics["resolved_count"] == 1
    assert metrics["brier_score"] == 0.0


@pytest.mark.parametrize(
    "confidence,realized,outcome_class",
    [
        pytest.param(0.25, False, "TRUE_NEGATIVE", id="interior-negative"),
        pytest.param(0.75, True, "TRUE_POSITIVE", id="interior-positive"),
    ],
)
def test_valid_interior_confidence_keeps_existing_binary_brier(
    confidence, realized, outcome_class
):
    case = _synthetic_case(
        confidence=confidence, realized=realized, outcome_class=outcome_class
    )
    assert replay_case(case)["realized_constraint"] is realized
    assert evaluate_cases([case])["brier_score"] == 0.0625


@pytest.mark.parametrize(
    "outcome_class,resolved_count,precision",
    [
        pytest.param("TRUE_POSITIVE", 1, 1.0, id="resolved-null-target"),
        pytest.param("UNRESOLVED", 0, None, id="unresolved-null-target"),
    ],
)
def test_none_target_retains_existing_resolved_and_unresolved_semantics(
    outcome_class, resolved_count, precision
):
    case = _synthetic_case(realized=None, outcome_class=outcome_class)
    assert replay_case(case)["realized_constraint"] is None
    metrics = evaluate_cases([case])
    assert metrics["brier_score"] is None
    assert metrics["resolved_count"] == resolved_count
    assert metrics["historical_coverage"] == resolved_count
    assert metrics["precision"] == precision


@pytest.mark.parametrize("realized", [True, False], ids=["bool-true", "bool-false"])
def test_unresolved_boolean_target_stays_outside_brier_denominator(realized):
    case = _synthetic_case(realized=realized, outcome_class="UNRESOLVED")
    assert replay_case(case)["realized_constraint"] is realized
    metrics = evaluate_cases([case])
    assert metrics["resolved_count"] == 0
    assert metrics["brier_score"] is None
    assert metrics["precision"] is None
    assert metrics["recall_where_observable"] is None


def test_none_target_does_not_change_existing_brier_denominator():
    cases = [
        _synthetic_case(confidence=1.0, realized=True),
        _synthetic_case(confidence=0.0, realized=False, outcome_class="TRUE_NEGATIVE"),
        _synthetic_case(confidence=0.8, realized=None),
    ]
    metrics = evaluate_cases(cases)
    assert metrics["case_count"] == 3
    assert metrics["resolved_count"] == 3
    assert metrics["brier_score"] == 0.0
    assert metrics["precision"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
