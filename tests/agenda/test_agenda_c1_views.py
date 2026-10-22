"""C1, the text on the mirror: agenda_lines in agenda/views.py.

Contract
--------
agenda_lines(events: list[Event], now: datetime, tz: tzinfo) -> list[str]

* One line per event, in the order given (it does not re-sort):

      "Today 3:30 PM  Dentist"         <day> <time>, TWO spaces, <title>
      "Sat All day  Birthday"          all-day events show "All day" as the time

* The <day> label counts local calendar days from today, in ``tz``:
      today          "Today"
      tomorrow       "Tomorrow"
      2 to 6 days    the weekday, "Thu"
      7 or more      month and day, "Oct 27", "Nov 3" (no leading zero)
  An event that has already started (it is in progress, or began yesterday and is
  still going) is labelled "Today".
* The time is 12-hour, no leading zero on the hour, minutes ALWAYS shown:
  00:00 -> "12:00 AM", 00:05 -> "12:05 AM", 12:00 -> "12:00 PM",
  13:05 -> "1:05 PM", 23:59 -> "11:59 PM". It is the event's time in ``tz``
  whatever zone the event object carries: a start given in UTC is converted
  first (and so is its date, for the label).
* No events -> ["Nothing coming up"].
* Titles are shown whole here. Shortening long titles comes later.
* ``now`` must be timezone-aware (ValueError otherwise).
* Pure: no tkinter, no clock, the input list is left alone.

2026-10-20 is a Tuesday. ``now`` is 12:00 noon that day in New York (EDT, UTC-4).
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from agenda.models import Event
from agenda.views import agenda_lines

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=NY)


def timed(title, month, day, hour, minute=0, minutes=60):
    start = datetime(2026, month, day, hour, minute, tzinfo=NY)
    return Event(title, start, start + timedelta(minutes=minutes))


def all_day(title, month, day, days=1):
    start = datetime(2026, month, day, tzinfo=NY)
    return Event(title, start, start + timedelta(days=days), all_day=True)


def lines(*events):
    return agenda_lines(list(events), NOW, NY)


# --------------------------------------------------------------------------
# Nothing to show
# --------------------------------------------------------------------------
def test_no_events_says_nothing_coming_up():
    assert agenda_lines([], NOW, NY) == ["Nothing coming up"]


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
def test_a_line_is_day_time_two_spaces_title():
    assert lines(timed("Dentist", 10, 20, 15, 30)) == ["Today 3:30 PM  Dentist"]


def test_an_all_day_event_shows_all_day_instead_of_a_time():
    assert lines(all_day("Birthday", 10, 24)) == ["Sat All day  Birthday"]


def test_one_line_per_event_in_the_order_given():
    result = lines(timed("B", 10, 22, 9), timed("A", 10, 21, 9))
    assert result == ["Thu 9:00 AM  B", "Tomorrow 9:00 AM  A"]


def test_titles_are_shown_whole():
    title = "Quarterly planning meeting with the whole department"
    assert lines(timed(title, 10, 21, 9)) == [f"Tomorrow 9:00 AM  {title}"]


@pytest.mark.parametrize(
    "hour, minute, expected",
    [
        (0, 0, "12:00 AM"),
        (0, 5, "12:05 AM"),
        (9, 30, "9:30 AM"),
        (12, 0, "12:00 PM"),
        (13, 5, "1:05 PM"),
        (23, 59, "11:59 PM"),
    ],
)
def test_twelve_hour_clock_without_a_leading_zero_and_with_minutes(hour, minute, expected):
    assert lines(timed("X", 10, 21, hour, minute)) == [f"Tomorrow {expected}  X"]


# --------------------------------------------------------------------------
# Day labels
# --------------------------------------------------------------------------
def test_today_and_tomorrow():
    result = lines(timed("A", 10, 20, 15), timed("B", 10, 21, 15))
    assert [line.split(" ")[0] for line in result] == ["Today", "Tomorrow"]


@pytest.mark.parametrize(
    "month, day, label",
    [
        (10, 22, "Thu"),   # 2 days ahead
        (10, 23, "Fri"),
        (10, 26, "Mon"),   # 6 days ahead
    ],
)
def test_within_a_week_the_weekday_is_shown(month, day, label):
    assert lines(timed("X", month, day, 9)) == [f"{label} 9:00 AM  X"]


@pytest.mark.parametrize(
    "month, day, label",
    [
        (10, 27, "Oct 27"),  # 7 days ahead
        (11, 3, "Nov 3"),    # no leading zero
        (11, 10, "Nov 10"),
        (11, 19, "Nov 19"),
    ],
)
def test_a_week_or_more_ahead_shows_month_and_day(month, day, label):
    assert lines(timed("X", month, day, 9)) == [f"{label} 9:00 AM  X"]


def test_the_label_counts_calendar_days_not_24_hour_blocks():
    # 11:30 PM tonight is "Today" even though it is only 11.5 hours away,
    # and 12:30 AM is already "Tomorrow".
    result = lines(timed("Late", 10, 20, 23, 30), timed("After midnight", 10, 21, 0, 30))
    assert result == ["Today 11:30 PM  Late", "Tomorrow 12:30 AM  After midnight"]


def test_an_event_in_progress_is_labelled_today():
    assert lines(timed("Meeting", 10, 20, 11, minutes=120)) == ["Today 11:00 AM  Meeting"]


def test_a_running_multi_day_event_is_labelled_today():
    conference = all_day("Conference", 10, 19, days=3)
    assert lines(conference) == ["Today All day  Conference"]


def test_an_all_day_event_today():
    assert lines(all_day("Holiday", 10, 20)) == ["Today All day  Holiday"]


# --------------------------------------------------------------------------
# Time zones
# --------------------------------------------------------------------------
def test_a_start_given_in_utc_is_shown_in_the_display_zone():
    # 14:30 UTC is 10:30 AM in New York.
    event = Event(
        "Call",
        datetime(2026, 10, 22, 14, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 22, 15, 30, tzinfo=timezone.utc),
    )
    assert lines(event) == ["Thu 10:30 AM  Call"]


def test_the_day_label_uses_the_local_date_not_the_utc_date():
    # 02:30 UTC on the 21st is 10:30 PM on the 20th in New York: today, not tomorrow.
    event = Event(
        "Late show",
        datetime(2026, 10, 21, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 21, 3, 30, tzinfo=timezone.utc),
    )
    assert lines(event) == ["Today 10:30 PM  Late show"]


def test_today_is_worked_out_in_the_display_zone_even_if_now_is_in_utc():
    now_in_utc = datetime(2026, 10, 21, 2, 30, tzinfo=timezone.utc)  # 10:30 PM on the 20th in NY
    result = agenda_lines([timed("Tomorrow morning", 10, 21, 9)], now_in_utc, NY)
    assert result == ["Tomorrow 9:00 AM  Tomorrow morning"]


# --------------------------------------------------------------------------
# Edges
# --------------------------------------------------------------------------
def test_today_comes_from_the_now_argument_not_the_machines_clock():
    march = datetime(2026, 3, 5, 12, 0, tzinfo=NY)
    start = datetime(2026, 3, 6, 9, 0, tzinfo=NY)
    event = Event("X", start, start + timedelta(hours=1))
    assert agenda_lines([event], march, NY) == ["Tomorrow 9:00 AM  X"]


def test_a_now_without_a_time_zone_is_a_value_error():
    with pytest.raises(ValueError):
        agenda_lines([timed("A", 10, 21, 9)], datetime(2026, 10, 20, 12, 0), NY)


def test_the_input_list_is_left_alone():
    events = [timed("B", 10, 22, 9), timed("A", 10, 21, 9)]
    before = list(events)
    agenda_lines(events, NOW, NY)
    assert events == before
