"""Tests for weather/state.py: what the weather panel remembers.

This is the logic that sits behind the tkinter widget, kept free of tkinter so
it can be tested without a window: which view is showing, whether data has
arrived yet, whether the data on screen is getting old, and whether the last
attempt to get fresh data failed.

Contract
--------
VIEWS = ("current", "hourly", "daily")

class WeatherState:
    WeatherState(stale_after, clock=time.monotonic)
        stale_after: seconds; must be > 0 (ValueError otherwise)
        clock: zero-argument function returning "now" in seconds

    .snapshot      the latest WeatherSnapshot, or None before the first one
    .view          name of the view that is showing; starts at "current"
    .is_loading    True until the first snapshot arrives
    .is_stale      True when the snapshot is older than stale_after seconds
                   (strictly older: exactly stale_after is still fresh);
                   False while there is no snapshot
    .last_fetch_failed
                   True when the most recent fetch attempt failed and no
                   successful one has happened since. False at start-up and
                   after every update(). Read-only (a property): it changes
                   only through mark_failed() and update().
    .update(snapshot)   store a new snapshot and restart its age;
                        clears last_fetch_failed
    .mark_failed()      a fetch failed: set last_fetch_failed, keep what we
                        have, do NOT restart the age
    .advance() -> str   move to the next view (wrapping around), return its name

Rotating views never touches the data or the failure flag, and new data never
changes which view is showing.

Why last_fetch_failed exists
----------------------------
"Loading" and "failed" are different things to show. Offline at start-up there
is no snapshot, so is_loading stays True, but last_fetch_failed tells the
widget to say "Weather unavailable" instead of "Loading..." forever. With old
data on screen, it lets the widget warn right away, long before is_stale.
"""
import pytest

from weather.state import VIEWS, WeatherState


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
    return WeatherState(stale_after=600, clock=clock)


SNAP_A = object()
SNAP_B = object()


def test_views_are_current_hourly_daily():
    assert VIEWS == ("current", "hourly", "daily")


# --------------------------------------------------------------------------
# Start-up
# --------------------------------------------------------------------------
def test_starts_in_the_loading_state(state):
    assert state.snapshot is None
    assert state.is_loading is True
    assert state.is_stale is False


def test_starts_on_the_current_view(state):
    assert state.view == "current"


def test_starts_without_a_failure(state):
    assert state.last_fetch_failed is False


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_stale_after_must_be_positive(clock, bad):
    with pytest.raises(ValueError):
        WeatherState(stale_after=bad, clock=clock)


def test_two_states_do_not_share_anything(clock):
    first = WeatherState(stale_after=600, clock=clock)
    second = WeatherState(stale_after=600, clock=clock)
    first.update(SNAP_A)
    first.advance()
    first.mark_failed()
    assert second.snapshot is None
    assert second.view == "current"
    assert second.last_fetch_failed is False
    assert second.is_loading is True


# --------------------------------------------------------------------------
# Updating
# --------------------------------------------------------------------------
def test_update_stores_the_snapshot_and_ends_loading(state):
    state.update(SNAP_A)
    assert state.snapshot is SNAP_A
    assert state.is_loading is False
    assert state.is_stale is False


def test_a_newer_snapshot_replaces_the_older_one(state):
    state.update(SNAP_A)
    state.update(SNAP_B)
    assert state.snapshot is SNAP_B


# --------------------------------------------------------------------------
# Rotation
# --------------------------------------------------------------------------
def test_advance_cycles_through_the_views_and_wraps(state):
    assert state.advance() == "hourly"
    assert state.view == "hourly"
    assert state.advance() == "daily"
    assert state.view == "daily"
    assert state.advance() == "current"
    assert state.view == "current"
    assert state.advance() == "hourly"


def test_advance_works_before_any_data_arrives(state):
    assert state.advance() == "hourly"
    assert state.snapshot is None
    assert state.is_loading is True


def test_advance_does_not_touch_the_data(state, clock):
    state.update(SNAP_A)
    clock.advance(100)
    for _ in range(5):
        state.advance()
    assert state.snapshot is SNAP_A
    assert state.is_stale is False


def test_new_data_does_not_reset_the_view(state):
    state.advance()
    state.advance()
    assert state.view == "daily"
    state.update(SNAP_A)
    assert state.view == "daily"


# --------------------------------------------------------------------------
# Staleness
# --------------------------------------------------------------------------
def test_fresh_at_exactly_stale_after(state, clock):
    state.update(SNAP_A)
    clock.advance(600)
    assert state.is_stale is False


def test_stale_just_after_stale_after(state, clock):
    state.update(SNAP_A)
    clock.advance(600.01)
    assert state.is_stale is True


def test_update_restarts_the_age(state, clock):
    state.update(SNAP_A)
    clock.advance(500)
    state.update(SNAP_B)
    clock.advance(500)
    assert state.is_stale is False
    clock.advance(101)
    assert state.is_stale is True


def test_stale_data_is_still_available(state, clock):
    state.update(SNAP_A)
    clock.advance(10_000)
    assert state.is_stale is True
    assert state.snapshot is SNAP_A
    assert state.is_loading is False


# --------------------------------------------------------------------------
# Failures: what mark_failed must leave alone
# --------------------------------------------------------------------------
def test_failure_keeps_the_last_good_data(state):
    state.update(SNAP_A)
    state.mark_failed()
    assert state.snapshot is SNAP_A
    assert state.is_loading is False


def test_failure_does_not_restart_the_age(state, clock):
    state.update(SNAP_A)
    clock.advance(400)
    state.mark_failed()
    clock.advance(201)
    assert state.is_stale is True


def test_failure_before_any_data_leaves_us_loading(state):
    state.mark_failed()
    assert state.snapshot is None
    assert state.is_loading is True
    assert state.is_stale is False


def test_failure_does_not_change_the_view(state):
    state.advance()
    state.mark_failed()
    assert state.view == "hourly"


# --------------------------------------------------------------------------
# Failures: the last_fetch_failed flag
# --------------------------------------------------------------------------
def test_mark_failed_sets_the_flag(state):
    state.mark_failed()
    assert state.last_fetch_failed is True


def test_failure_before_any_data_is_visible_as_failed_not_just_loading(state):
    state.mark_failed()
    assert state.is_loading is True
    assert state.last_fetch_failed is True


def test_failure_with_data_on_screen_sets_the_flag_and_keeps_the_data(state):
    state.update(SNAP_A)
    state.mark_failed()
    assert state.last_fetch_failed is True
    assert state.snapshot is SNAP_A
    assert state.is_stale is False  # age is a separate question


def test_repeated_failures_keep_the_flag_set(state):
    for _ in range(3):
        state.mark_failed()
    assert state.last_fetch_failed is True


def test_update_clears_the_flag(state):
    state.mark_failed()
    state.update(SNAP_A)
    assert state.last_fetch_failed is False


def test_update_clears_the_flag_when_data_was_already_there(state):
    state.update(SNAP_A)
    state.mark_failed()
    state.update(SNAP_B)
    assert state.last_fetch_failed is False
    assert state.snapshot is SNAP_B


def test_a_failure_after_recovery_sets_the_flag_again(state):
    state.mark_failed()
    state.update(SNAP_A)
    state.mark_failed()
    assert state.last_fetch_failed is True


def test_advance_does_not_touch_the_flag(state):
    state.advance()
    assert state.last_fetch_failed is False
    state.mark_failed()
    state.advance()
    assert state.last_fetch_failed is True


def test_the_flag_is_read_only(state):
    with pytest.raises(AttributeError):
        state.last_fetch_failed = True


def test_the_flag_does_not_depend_on_the_clock(state, clock):
    state.update(SNAP_A)
    state.mark_failed()
    clock.advance(10_000)
    assert state.last_fetch_failed is True
    assert state.is_stale is True