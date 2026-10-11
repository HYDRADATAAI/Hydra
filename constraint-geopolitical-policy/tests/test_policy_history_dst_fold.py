import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from hydra_constraint_policy.model import (
    EventType,
    HistoricalEvent,
    Provenance,
    TemporalFacts,
    ValidationError,
    active_events_as_of,
    eligible_as_of,
)


class RepeatedHour(tzinfo):
    """A tiny fallback timezone with two instants at the same local wall time."""

    def utcoffset(self, dt):
        return timedelta(hours=-4 if dt is None or dt.fold == 0 else -5)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "TEST-FOLD"


FOLD = RepeatedHour()
EARLY = datetime(2024, 11, 3, 1, 30, tzinfo=FOLD, fold=0)
LATE = datetime(2024, 11, 3, 1, 30, tzinfo=FOLD, fold=1)


def _event(*, known_at=EARLY, available_at=EARLY, effective_at=None, resolved_at=None):
    return HistoricalEvent(
        event_id="evt-fold",
        event_type=EventType.EXPORT_CONTROL,
        title="Repeated-hour test",
        temporal=TemporalFacts(
            known_at=known_at,
            effective_at=effective_at,
            resolved_at=resolved_at,
        ),
        provenance=(
            Provenance(
                "source",
                "doc",
                available_at,
                available_at,
                "v1",
                "sha256:test",
            ),
        ),
    )


class PolicyHistoryDstFoldTests(unittest.TestCase):
    def test_later_known_at_in_repeated_hour_is_not_eligible(self):
        self.assertLess(EARLY.astimezone(timezone.utc), LATE.astimezone(timezone.utc))
        self.assertEqual([], eligible_as_of([_event(known_at=LATE)], EARLY))

    def test_later_provenance_is_not_chronologically_valid(self):
        with self.assertRaisesRegex(ValidationError, "known_at precedes all available evidence"):
            eligible_as_of([_event(known_at=EARLY, available_at=LATE)], EARLY)

    def test_future_effective_time_in_repeated_hour_is_not_active(self):
        self.assertEqual([], active_events_as_of([_event(effective_at=LATE)], EARLY))

    def test_later_resolution_in_repeated_hour_does_not_hide_active_event(self):
        event = _event(effective_at=EARLY, resolved_at=LATE)
        self.assertEqual([event], active_events_as_of([event], EARLY))

    def test_resolution_before_effective_uses_absolute_instants(self):
        with self.assertRaisesRegex(ValidationError, "resolved_at precedes effective_at"):
            _event(effective_at=LATE, resolved_at=EARLY).validate()

    def test_cutoff_must_be_timezone_aware(self):
        with self.assertRaisesRegex(ValidationError, "timezone-aware"):
            eligible_as_of([], datetime(2024, 11, 3, 1, 30))


if __name__ == "__main__":
    unittest.main()
