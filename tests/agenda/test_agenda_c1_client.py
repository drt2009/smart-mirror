"""C1, fetching: fetch_calendar in agenda/client.py.

Contract
--------
agenda/client.py does ``from ical.calendar_stream import IcsCalendarStream`` at
module level and defines

    class CalendarFetchError(Exception)
    async def fetch_calendar(url, timeout=<positive number>) -> Calendar

* It makes ONE call, ``IcsCalendarStream.calendar_from_url(url)``, through that
  module-level name so the tests can swap the library for a fake. No test here
  touches the network. The url is passed through unchanged as the first argument.
* It returns exactly the calendar object the library gave back.
* ANY failure (connection error, timeout, bad status, a parse error, anything
  else the library raises) comes out as CalendarFetchError.
* The error NEVER contains the URL, neither in its message nor anywhere in the
  printed traceback. The URL is a secret, and the library's own error messages
  include it ("Failed to fetch calendar from url '...'"). Python prints chained
  exceptions in a traceback, so the original error must not be chained: use
  ``raise ... from None``.
* ``timeout`` (seconds) is a hard limit on the whole fetch. A request that never
  answers ends with CalendarFetchError once the timeout has passed. Its default is
  a positive number, so a stalled connection cannot hang the worker thread forever.
* Cancelling the task is not an error to translate: CancelledError passes through.
"""
import asyncio
import inspect
import time
import traceback
from types import SimpleNamespace

import pytest

from agenda import client
from agenda.client import CalendarFetchError, fetch_calendar

URL = "https://calendar.google.com/calendar/ical/me%40example.com/private-abc123secret/basic.ics"
CALENDAR = object()


@pytest.fixture(autouse=True)
def fake_library(monkeypatch):
    """Replaces the library in every test, so nothing here can reach the network."""
    behaviour = SimpleNamespace(calls=[], result=CALENDAR, error=None, hang=False)

    class FakeStream:
        @classmethod
        async def calendar_from_url(cls, url, *args, **kwargs):
            behaviour.calls.append((url, args, kwargs))
            if behaviour.hang:
                await asyncio.sleep(3600)
            if behaviour.error is not None:
                raise behaviour.error
            return behaviour.result

    monkeypatch.setattr(client, "IcsCalendarStream", FakeStream)
    return behaviour


def run(coroutine):
    return asyncio.run(coroutine)


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------
def test_fetch_calendar_is_a_coroutine_function():
    assert inspect.iscoroutinefunction(fetch_calendar)


def test_it_returns_the_calendar_the_library_returned(fake_library):
    assert run(fetch_calendar(URL)) is CALENDAR


def test_it_makes_one_call_with_the_url_unchanged(fake_library):
    run(fetch_calendar(URL))
    assert len(fake_library.calls) == 1
    assert fake_library.calls[0][0] == URL


def test_a_fast_answer_is_not_cut_off_by_a_short_timeout(fake_library):
    assert run(fetch_calendar(URL, timeout=0.5)) is CALENDAR


# --------------------------------------------------------------------------
# Failures
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "error",
    [
        OSError("connection reset"),
        TimeoutError(),
        ValueError("not a calendar"),
        RuntimeError("something else"),
        Exception("plain"),
    ],
    ids=["oserror", "timeout", "valueerror", "runtimeerror", "exception"],
)
def test_any_library_failure_becomes_a_calendar_fetch_error(fake_library, error):
    fake_library.error = error
    with pytest.raises(CalendarFetchError):
        run(fetch_calendar(URL))


def test_the_error_message_does_not_contain_the_url(fake_library):
    fake_library.error = OSError(f"Failed to fetch calendar from url {URL!r}: boom")
    with pytest.raises(CalendarFetchError) as info:
        run(fetch_calendar(URL))
    assert URL not in str(info.value)
    assert "private-" not in str(info.value)
    assert str(info.value) != ""


def test_the_printed_traceback_does_not_contain_the_url(fake_library):
    # The library's own error carries the URL. If it is chained to ours, it is
    # printed with the traceback and ends up in the logs.
    fake_library.error = OSError(f"Failed to fetch calendar from url {URL!r}: boom")
    with pytest.raises(CalendarFetchError) as info:
        run(fetch_calendar(URL))
    printed = "".join(traceback.format_exception(info.value))
    assert "private-" not in printed
    assert "abc123secret" not in printed


# --------------------------------------------------------------------------
# Timeout and cancellation
# --------------------------------------------------------------------------
def test_the_default_timeout_is_a_positive_number():
    default = inspect.signature(fetch_calendar).parameters["timeout"].default
    assert isinstance(default, (int, float)) and default > 0


def test_a_request_that_never_answers_ends_with_a_fetch_error(fake_library):
    fake_library.hang = True
    started = time.monotonic()

    async def attempt():
        return await asyncio.wait_for(fetch_calendar(URL, timeout=0.05), timeout=2)

    with pytest.raises(CalendarFetchError):
        run(attempt())
    assert time.monotonic() - started < 1.5


def test_the_timeout_error_does_not_contain_the_url(fake_library):
    fake_library.hang = True

    async def attempt():
        return await asyncio.wait_for(fetch_calendar(URL, timeout=0.05), timeout=2)

    with pytest.raises(CalendarFetchError) as info:
        run(attempt())
    assert "private-" not in "".join(traceback.format_exception(info.value))


def test_cancelling_the_task_is_not_turned_into_a_fetch_error(fake_library):
    fake_library.hang = True

    async def attempt():
        task = asyncio.ensure_future(fetch_calendar(URL, timeout=30))
        await asyncio.sleep(0.05)
        task.cancel()
        return await asyncio.wait_for(task, timeout=2)

    with pytest.raises(asyncio.CancelledError):
        run(attempt())
