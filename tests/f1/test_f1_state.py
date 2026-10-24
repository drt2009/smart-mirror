"""F1State in f1/state.py: what the F1 part of the mirror currently knows.

Contract
--------
F1State(stale_after, clock=time.monotonic)

* ``stale_after`` is a number of seconds and must be greater than zero, otherwise
  ValueError WITH a message.
* .race           the UpcomingRace last stored, or None. None before the first
                  update AND after an update with None (season over).
* .is_loading     True until the first update() has happened. update(None) counts:
                  "no race left" is an answer, not still loading.
* .update(race)   store the race (or None), remember when (clock), clear a failed flag.
* .mark_failed()  the latest fetch failed. The old race stays available.
* .last_fetch_failed   True after mark_failed(), until the next update().
* .is_stale       False before the first update; afterwards True only when the last
                  update is STRICTLY older than stale_after seconds.

No clock is read except through ``clock``. The state module does no network or
tkinter work, so everything here runs without a window.
"""
from datetime import datetime, timezone

import pytest

from f1.models import UpcomingRace
from f1.state import F1State


def make_race(name="Miami Grand Prix"):
    return UpcomingRace(
        race_name=name,
        circuit_name="Miami International Autodrome",
        country="USA",
        race_date=datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc),
        sprint_race=False,
    )


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def state(clock):
    return F1State(600, clock=clock)


class TestConstruction:
    @pytest.mark.parametrize("bad", [0, -1, -0.5])
    def test_stale_after_must_be_positive(self, bad):
        with pytest.raises(ValueError) as raised:
            F1State(bad)
        assert str(raised.value)

    def test_a_tiny_positive_value_is_fine(self):
        F1State(0.001)

    def test_the_default_clock_works(self):
        s = F1State(60)
        s.update(make_race())
        assert s.is_stale is False


class TestBeforeAnyUpdate:
    def test_it_is_loading(self, state):
        assert state.is_loading is True

    def test_there_is_no_race(self, state):
        assert state.race is None

    def test_it_has_not_failed(self, state):
        assert state.last_fetch_failed is False

    def test_it_is_not_stale(self, state, clock):
        clock.advance(10**6)
        assert state.is_stale is False


class TestUpdating:
    def test_the_race_is_stored(self, state):
        race = make_race()
        state.update(race)
        assert state.race is race

    def test_loading_ends_after_the_first_update(self, state):
        state.update(make_race())
        assert state.is_loading is False

    def test_a_season_over_update_with_none_also_ends_loading(self, state):
        state.update(None)
        assert state.is_loading is False
        assert state.race is None

    def test_a_later_update_replaces_the_race(self, state):
        state.update(make_race("First Grand Prix"))
        newer = make_race("Second Grand Prix")
        state.update(newer)
        assert state.race is newer

    def test_a_none_update_clears_the_old_race(self, state):
        state.update(make_race())
        state.update(None)
        assert state.race is None
        assert state.is_loading is False

    def test_the_clock_is_read_only_through_the_injected_clock(self, clock):
        calls = []

        def counting_clock():
            calls.append(1)
            return clock()

        s = F1State(600, clock=counting_clock)
        s.update(make_race())
        assert calls


class TestFailures:
    def test_mark_failed_sets_the_flag(self, state):
        state.mark_failed()
        assert state.last_fetch_failed is True

    def test_a_failure_before_any_data_is_still_loading(self, state):
        state.mark_failed()
        assert state.is_loading is True
        assert state.race is None

    def test_the_old_race_survives_a_failure(self, state):
        race = make_race()
        state.update(race)
        state.mark_failed()
        assert state.race is race
        assert state.is_loading is False

    def test_a_successful_update_clears_the_flag(self, state):
        state.mark_failed()
        state.update(make_race())
        assert state.last_fetch_failed is False

    def test_a_none_update_clears_the_flag_too(self, state):
        state.mark_failed()
        state.update(None)
        assert state.last_fetch_failed is False

    def test_a_failure_does_not_refresh_the_age(self, state, clock):
        state.update(make_race())
        clock.advance(601)
        state.mark_failed()
        assert state.is_stale is True


class TestStaleness:
    def test_fresh_data_is_not_stale(self, state, clock):
        state.update(make_race())
        clock.advance(10)
        assert state.is_stale is False

    def test_exactly_the_limit_is_not_stale(self, state, clock):
        state.update(make_race())
        clock.advance(600)
        assert state.is_stale is False

    def test_just_past_the_limit_is_stale(self, state, clock):
        state.update(make_race())
        clock.advance(600.001)
        assert state.is_stale is True

    def test_a_new_update_makes_it_fresh_again(self, state, clock):
        state.update(make_race())
        clock.advance(10_000)
        assert state.is_stale is True
        state.update(make_race())
        assert state.is_stale is False

    def test_a_none_update_also_resets_the_age(self, state, clock):
        state.update(make_race())
        clock.advance(10_000)
        state.update(None)
        assert state.is_stale is False
