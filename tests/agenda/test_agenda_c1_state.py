"""C1, keeping the latest events: AgendaState in agenda/state.py.

Contract
--------
AgendaState(stale_after, clock=time.monotonic)

* ``stale_after`` is a number of seconds and must be greater than zero, otherwise
  ValueError WITH a message.
* The state holds the finished list of Event objects, not the library's calendar:
  parsing happens in the worker thread, so the UI thread only ever reads a list.
  The state module does not import the parser.
* .events         a list of the Events last stored; [] before the first update.
                  It is a copy: changing the returned list does not change the state.
* .is_loading     True until the first update() has happened. An update with an
                  EMPTY list still counts: the calendar was read and nothing is
                  coming up, which is not the same as still loading.
* .update(events) store the events, remember when (clock), clear a failed flag.
* .mark_failed()  the latest fetch failed. The old events stay available.
* .last_fetch_failed   True after mark_failed(), until the next update().
* .is_stale       False before the first update; afterwards True only when the
                  last update is STRICTLY older than stale_after seconds.

No clock is read except through ``clock``, so the tests pass a fake one.
"""
from datetime import datetime, timedelta, timezone

import pytest

from agenda.models import Event
from agenda.state import AgendaState

UTC = timezone.utc


def event(title="A"):
    start = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)
    return Event(title, start, start + timedelta(hours=1))


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
    return AgendaState(600, clock=clock)


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [0, -1, -600])
def test_stale_after_must_be_greater_than_zero(bad):
    with pytest.raises(ValueError) as info:
        AgendaState(bad)
    assert str(info.value) != ""


def test_it_can_be_built_with_just_stale_after():
    assert AgendaState(600).is_loading is True


# --------------------------------------------------------------------------
# Before and after the first update
# --------------------------------------------------------------------------
def test_a_new_state_is_loading_with_no_events_and_no_failure(state):
    assert state.is_loading is True
    assert state.events == []
    assert state.last_fetch_failed is False
    assert state.is_stale is False


def test_update_stores_the_events_and_ends_loading(state):
    state.update([event("A"), event("B")])
    assert state.is_loading is False
    assert [e.title for e in state.events] == ["A", "B"]


def test_an_empty_update_is_not_loading(state):
    state.update([])
    assert state.is_loading is False
    assert state.events == []


def test_a_later_update_replaces_the_events(state):
    state.update([event("Old")])
    state.update([event("New")])
    assert [e.title for e in state.events] == ["New"]


def test_the_events_property_returns_a_copy(state):
    state.update([event("A")])
    state.events.append(event("Extra"))
    assert [e.title for e in state.events] == ["A"]


def test_changing_the_list_passed_to_update_does_not_change_the_state(state):
    given = [event("A")]
    state.update(given)
    given.append(event("Extra"))
    assert [e.title for e in state.events] == ["A"]


# --------------------------------------------------------------------------
# Failures
# --------------------------------------------------------------------------
def test_a_failure_before_any_data_leaves_it_loading_and_flags_the_failure(state):
    state.mark_failed()
    assert state.last_fetch_failed is True
    assert state.is_loading is True
    assert state.events == []


def test_a_failure_keeps_the_old_events(state):
    state.update([event("Kept")])
    state.mark_failed()
    assert state.last_fetch_failed is True
    assert state.is_loading is False
    assert [e.title for e in state.events] == ["Kept"]


def test_a_successful_update_clears_the_failure(state):
    state.mark_failed()
    state.update([event("A")])
    assert state.last_fetch_failed is False


def test_a_failure_does_not_make_the_data_fresh(state, clock):
    state.update([event("A")])
    clock.advance(601)
    state.mark_failed()
    assert state.is_stale is True


# --------------------------------------------------------------------------
# Going stale
# --------------------------------------------------------------------------
def test_fresh_data_is_not_stale(state, clock):
    state.update([event("A")])
    clock.advance(599)
    assert state.is_stale is False


def test_data_exactly_stale_after_seconds_old_is_not_yet_stale(state, clock):
    state.update([event("A")])
    clock.advance(600)
    assert state.is_stale is False


def test_data_older_than_stale_after_is_stale(state, clock):
    state.update([event("A")])
    clock.advance(601)
    assert state.is_stale is True


def test_a_new_update_makes_the_data_fresh_again(state, clock):
    state.update([event("A")])
    clock.advance(601)
    state.update([event("B")])
    assert state.is_stale is False


def test_an_empty_update_also_resets_the_age(state, clock):
    state.update([event("A")])
    clock.advance(601)
    state.update([])
    assert state.is_stale is False


def test_the_state_does_not_import_the_parser():
    import agenda.state as module

    assert not hasattr(module, "parse")
    assert not hasattr(module, "upcoming")
