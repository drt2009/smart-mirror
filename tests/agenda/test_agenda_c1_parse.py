"""C1, picking the events: upcoming() in agenda/parse.py, and the Event model.

Contract
--------
agenda/models.py

    @dataclass(frozen=True)
    class Event:
        title: str
        start: datetime        # timezone-aware, in the display time zone
        end: datetime          # timezone-aware, in the display time zone
        all_day: bool = False

agenda/parse.py

    upcoming(calendar, now, tz, limit=5, days=30) -> list[Event]

``calendar`` is the object IcsCalendarStream gives back (these tests build one
from inline .ics text). ``now`` is an aware datetime, ``tz`` the zone the mirror
shows times in (a zoneinfo zone, so daylight saving counts).

* The window: an event is returned when it has not ended yet (end > now) and
  starts before now + days (compared on the clock in ``tz``). Events in progress
  are therefore included, events that ended at or before ``now`` are not, and an
  event starting exactly at the end of the window is not.
* The result is sorted by start time. Equal starts: all-day events first, then by
  title A to Z. At most ``limit`` events come back (the earliest ones).
  limit < 1 and days < 1 are ValueErrors; so is a ``now`` with no time zone.
* Recurring events are expanded: each occurrence in the window is its own Event,
  cancelled occurrences (EXDATE) are left out and moved ones (RECURRENCE-ID)
  appear at their new time. A series that never ends must not hang the call.
* Start and end are converted to ``tz``: a 13:30 UTC event is 9:30 AM in New York
  in October (UTC-4) and 8:30 AM in December (UTC-5). Zone-less ("floating") times
  are taken to be in ``tz``. The library's own system-zone default is never used.
* All-day events have all_day=True; start is midnight of the first day in ``tz``
  and end is midnight AFTER the last day (iCalendar's end date is exclusive). An
  all-day event that covers today is "in progress"; one that ended at midnight
  this morning is over.
* A missing, empty or blank title becomes "(No title)"; titles are trimmed;
  escaped characters in the feed (``\\,``) come back unescaped.
* No network, no clock: the calendar, ``now`` and ``tz`` are the only inputs.

2026-10-20 is a Tuesday. New York is on EDT (UTC-4) until 2026-11-01 02:00, then
on EST (UTC-5). ``now`` is 12:00 noon on 2026-10-20 in the tests unless stated.
"""
import itertools
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from ical.calendar_stream import IcsCalendarStream

from agenda.models import Event
from agenda.parse import upcoming

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=NY)
_ids = itertools.count(1)


# --------------------------------------------------------------------------
# Building feeds. Times are written as New York wall-clock times and turned into
# the UTC form Google really uses.
# --------------------------------------------------------------------------
def utc_text(year, month, day, hour=0, minute=0):
    local = datetime(year, month, day, hour, minute, tzinfo=NY)
    return local.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def starts(*when, prop="DTSTART"):
    return f"{prop}:{utc_text(*when)}"


def ends(*when):
    return starts(*when, prop="DTEND")


def date_only(prop, year, month, day):
    return f"{prop};VALUE=DATE:{year:04d}{month:02d}{day:02d}"


def vevent(summary, *lines, uid=None):
    props = [f"UID:{uid or 'event-%d' % next(_ids)}", "DTSTAMP:20261001T000000Z", *lines]
    if summary is not None:
        props.append(f"SUMMARY:{summary}")
    return "BEGIN:VEVENT\r\n" + "".join(f"{p}\r\n" for p in props) + "END:VEVENT\r\n"


def meeting(summary, month, day, hour, minute=0, minutes=60):
    """A one-hour (by default) event starting at that New York wall-clock time."""
    start = datetime(2026, month, day, hour, minute, tzinfo=NY)
    end = start + timedelta(minutes=minutes)
    return vevent(
        summary,
        starts(start.year, start.month, start.day, start.hour, start.minute),
        ends(end.year, end.month, end.day, end.hour, end.minute),
    )


def feed(*vevents):
    text = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//tests//EN\r\n"
        + "".join(vevents)
        + "END:VCALENDAR\r\n"
    )
    return IcsCalendarStream.calendar_from_ics(text)


def titles(events):
    return [event.title for event in events]


# --------------------------------------------------------------------------
# Which events, in which order
# --------------------------------------------------------------------------
def test_an_empty_calendar_gives_an_empty_list():
    assert upcoming(feed(), NOW, NY) == []


def test_events_come_back_as_event_objects_in_a_list():
    result = upcoming(feed(meeting("A", 10, 21, 9)), NOW, NY)
    assert isinstance(result, list)
    assert all(isinstance(event, Event) for event in result)


def test_events_are_sorted_by_start_whatever_the_file_order():
    calendar = feed(
        meeting("Third", 10, 23, 9),
        meeting("First", 10, 20, 15),
        meeting("Second", 10, 21, 9),
    )
    assert titles(upcoming(calendar, NOW, NY)) == ["First", "Second", "Third"]


def test_an_event_that_has_ended_is_left_out():
    calendar = feed(meeting("Morning", 10, 20, 9), meeting("Afternoon", 10, 20, 15))
    assert titles(upcoming(calendar, NOW, NY)) == ["Afternoon"]


def test_an_event_ending_exactly_now_counts_as_ended():
    calendar = feed(meeting("Just done", 10, 20, 11), meeting("Next", 10, 20, 15))
    assert titles(upcoming(calendar, NOW, NY)) == ["Next"]


def test_an_event_in_progress_is_included_and_comes_first():
    calendar = feed(meeting("Soon", 10, 20, 15), meeting("Now", 10, 20, 11, minutes=120))
    assert titles(upcoming(calendar, NOW, NY)) == ["Now", "Soon"]


def test_an_event_starting_exactly_now_is_included():
    assert titles(upcoming(feed(meeting("Starting", 10, 20, 12)), NOW, NY)) == ["Starting"]


def test_an_event_that_started_yesterday_and_runs_into_today_is_included():
    overnight = vevent("Overnight", starts(2026, 10, 19, 22), ends(2026, 10, 20, 13))
    assert titles(upcoming(feed(overnight), NOW, NY)) == ["Overnight"]


# --------------------------------------------------------------------------
# The 30 day window, and the limit
# --------------------------------------------------------------------------
def test_the_default_window_is_30_days():
    calendar = feed(
        meeting("29 days", 11, 18, 12),
        meeting("31 days", 11, 20, 12),
    )
    assert titles(upcoming(calendar, NOW, NY)) == ["29 days"]


def test_an_event_just_inside_the_window_is_included_and_one_at_its_end_is_not():
    calendar = feed(
        meeting("Inside", 10, 27, 11, 59),
        meeting("Exactly at the end", 10, 27, 12),
        meeting("After", 10, 28, 9),
    )
    assert titles(upcoming(calendar, NOW, NY, days=7)) == ["Inside"]


def test_the_default_limit_is_five_and_keeps_the_earliest():
    calendar = feed(*[meeting(f"E{n}", 10, 20 + n, 15) for n in range(1, 9)])
    assert titles(upcoming(calendar, NOW, NY)) == ["E1", "E2", "E3", "E4", "E5"]


def test_the_limit_can_be_changed():
    calendar = feed(*[meeting(f"E{n}", 10, 20 + n, 15) for n in range(1, 6)])
    assert titles(upcoming(calendar, NOW, NY, limit=2)) == ["E1", "E2"]


def test_fewer_events_than_the_limit_returns_them_all():
    calendar = feed(meeting("A", 10, 21, 9), meeting("B", 10, 22, 9))
    assert len(upcoming(calendar, NOW, NY, limit=5)) == 2


def test_limit_is_applied_after_sorting_not_to_the_first_five_in_the_file():
    calendar = feed(*[meeting(f"Late{n}", 11, n, 9) for n in range(1, 7)] + [meeting("Early", 10, 21, 9)])
    assert titles(upcoming(calendar, NOW, NY, limit=1)) == ["Early"]


@pytest.mark.parametrize("bad", [0, -1])
def test_limit_must_be_at_least_one(bad):
    with pytest.raises(ValueError):
        upcoming(feed(), NOW, NY, limit=bad)


@pytest.mark.parametrize("bad", [0, -1])
def test_days_must_be_at_least_one(bad):
    with pytest.raises(ValueError):
        upcoming(feed(), NOW, NY, days=bad)


def test_a_now_without_a_time_zone_is_a_value_error():
    with pytest.raises(ValueError):
        upcoming(feed(meeting("A", 10, 21, 9)), datetime(2026, 10, 20, 12, 0), NY)


def test_now_may_be_given_in_another_zone():
    calendar = feed(meeting("Morning", 10, 20, 9), meeting("Afternoon", 10, 20, 15))
    in_utc = NOW.astimezone(timezone.utc)
    assert titles(upcoming(calendar, in_utc, NY)) == ["Afternoon"]


def test_the_window_is_measured_on_the_clock_in_the_display_zone_even_if_now_is_in_utc():
    # 30 days after noon on 20 Oct is noon on 19 Nov in New York, and the clocks go
    # back in between, so that is 30 days and one hour of elapsed time. An event at
    # 11:30 AM on 19 Nov is inside the window; 12:30 PM is outside it.
    calendar = feed(meeting("Inside", 11, 19, 11, 30), meeting("Outside", 11, 19, 12, 30))
    in_utc = NOW.astimezone(timezone.utc)
    assert titles(upcoming(calendar, in_utc, NY)) == ["Inside"]


def test_it_uses_the_now_it_is_given_not_the_machines_clock():
    # A "now" far from the real date: only an implementation that reads the real
    # clock would notice the difference.
    january = datetime(2026, 1, 5, 12, 0, tzinfo=NY)
    calendar = feed(
        vevent("Next day", starts(2026, 1, 6, 9), ends(2026, 1, 6, 10)),
        vevent("Months later", starts(2026, 10, 21, 9), ends(2026, 10, 21, 10)),
    )
    assert titles(upcoming(calendar, january, NY)) == ["Next day"]


def test_calling_twice_gives_the_same_answer():
    calendar = feed(meeting("A", 10, 21, 9), meeting("B", 10, 22, 9))
    assert upcoming(calendar, NOW, NY) == upcoming(calendar, NOW, NY)


# --------------------------------------------------------------------------
# Time zones
# --------------------------------------------------------------------------
def test_a_utc_time_is_converted_to_local_time():
    calendar = feed(vevent("Dentist", "DTSTART:20261021T133000Z", "DTEND:20261021T143000Z"))
    [event] = upcoming(calendar, NOW, NY)
    assert (event.start.hour, event.start.minute) == (9, 30)
    assert (event.end.hour, event.end.minute) == (10, 30)
    assert event.start.utcoffset() == timedelta(hours=-4)
    assert (event.start.year, event.start.month, event.start.day) == (2026, 10, 21)


def test_the_local_date_can_differ_from_the_utc_date():
    # 02:30 UTC on the 21st is 10:30 PM on the 20th in New York.
    calendar = feed(vevent("Late show", "DTSTART:20261021T023000Z", "DTEND:20261021T033000Z"))
    [event] = upcoming(calendar, NOW, NY)
    assert (event.start.day, event.start.hour) == (20, 22)


def test_daylight_saving_is_applied_per_event():
    calendar = feed(
        vevent("Before", "DTSTART:20261030T140000Z", "DTEND:20261030T150000Z"),
        vevent("After", "DTSTART:20261102T140000Z", "DTEND:20261102T150000Z"),
    )
    before, after = upcoming(calendar, NOW, NY)
    assert (before.start.hour, before.start.utcoffset()) == (10, timedelta(hours=-4))
    assert (after.start.hour, after.start.utcoffset()) == (9, timedelta(hours=-5))


def test_a_time_with_its_own_zone_is_converted_to_the_display_zone():
    # 14:00 in London on 22 Oct (still summer time, UTC+1) is 9:00 AM in New York.
    london = vevent(
        "London call",
        "DTSTART;TZID=Europe/London:20261022T140000",
        "DTEND;TZID=Europe/London:20261022T150000",
    )
    [event] = upcoming(feed(london), NOW, NY)
    assert (event.start.hour, event.start.utcoffset()) == (9, timedelta(hours=-4))


def test_a_time_with_no_zone_is_taken_to_be_in_the_display_zone():
    floating = vevent("Floating", "DTSTART:20261021T093000", "DTEND:20261021T103000")
    [event] = upcoming(feed(floating), NOW, NY)
    assert (event.start.hour, event.start.minute) == (9, 30)
    assert event.start.utcoffset() == timedelta(hours=-4)


def test_the_display_zone_is_the_one_given_not_the_machines():
    calendar = feed(vevent("Call", "DTSTART:20261021T133000Z", "DTEND:20261021T143000Z"))
    [event] = upcoming(calendar, NOW, ZoneInfo("Europe/London"))
    assert (event.start.hour, event.start.minute) == (14, 30)


def test_timed_events_are_not_all_day():
    [event] = upcoming(feed(meeting("A", 10, 21, 9)), NOW, NY)
    assert event.all_day is False


# --------------------------------------------------------------------------
# All-day events
# --------------------------------------------------------------------------
def test_an_all_day_event_runs_from_local_midnight_to_the_next_local_midnight():
    birthday = vevent("Birthday", date_only("DTSTART", 2026, 10, 22), date_only("DTEND", 2026, 10, 23))
    [event] = upcoming(feed(birthday), NOW, NY)
    assert event.all_day is True
    assert event.start == datetime(2026, 10, 22, tzinfo=NY)
    assert event.end == datetime(2026, 10, 23, tzinfo=NY)
    assert event.start.utcoffset() == timedelta(hours=-4)


def test_a_multi_day_all_day_event_ends_at_midnight_after_its_last_day():
    trip = vevent("Trip", date_only("DTSTART", 2026, 10, 30), date_only("DTEND", 2026, 11, 2))
    [event] = upcoming(feed(trip), NOW, NY)
    assert event.start == datetime(2026, 10, 30, tzinfo=NY)
    assert event.end == datetime(2026, 11, 2, tzinfo=NY)


def test_an_all_day_event_today_is_still_upcoming():
    today = vevent("Holiday", date_only("DTSTART", 2026, 10, 20), date_only("DTEND", 2026, 10, 21))
    assert titles(upcoming(feed(today), NOW, NY)) == ["Holiday"]


def test_an_all_day_event_that_ended_this_morning_is_left_out():
    yesterday = vevent("Yesterday", date_only("DTSTART", 2026, 10, 19), date_only("DTEND", 2026, 10, 20))
    assert upcoming(feed(yesterday), NOW, NY) == []


def test_a_running_multi_day_event_is_included():
    conference = vevent("Conference", date_only("DTSTART", 2026, 10, 19), date_only("DTEND", 2026, 10, 22))
    assert titles(upcoming(feed(conference), NOW, NY)) == ["Conference"]


def test_an_all_day_event_sorts_before_a_timed_event_starting_at_the_same_moment():
    # The titles are chosen so that sorting by title alone would give the other order.
    midnight = vevent("Apple movie", starts(2026, 10, 21, 0), ends(2026, 10, 21, 2))
    holiday = vevent("Zebra day", date_only("DTSTART", 2026, 10, 21), date_only("DTEND", 2026, 10, 22))
    assert titles(upcoming(feed(midnight, holiday), NOW, NY)) == ["Zebra day", "Apple movie"]


# --------------------------------------------------------------------------
# Titles and odd entries
# --------------------------------------------------------------------------
def test_equal_starts_are_ordered_by_title():
    calendar = feed(meeting("Banana", 10, 21, 9), meeting("Apple", 10, 21, 9))
    assert titles(upcoming(calendar, NOW, NY)) == ["Apple", "Banana"]


def test_a_missing_title_becomes_no_title():
    untitled = vevent(None, starts(2026, 10, 21, 9), ends(2026, 10, 21, 10))
    assert titles(upcoming(feed(untitled), NOW, NY)) == ["(No title)"]


@pytest.mark.parametrize("blank", ["", "   "])
def test_an_empty_or_blank_title_becomes_no_title(blank):
    untitled = vevent(blank, starts(2026, 10, 21, 9), ends(2026, 10, 21, 10))
    assert titles(upcoming(feed(untitled), NOW, NY)) == ["(No title)"]


def test_titles_are_trimmed():
    assert titles(upcoming(feed(meeting("  Dentist  ", 10, 21, 9)), NOW, NY)) == ["Dentist"]


def test_escaped_characters_in_a_title_are_unescaped():
    calendar = feed(meeting("Lunch\\, with Sam", 10, 21, 12))
    assert titles(upcoming(calendar, NOW, NY)) == ["Lunch, with Sam"]


def test_an_event_with_no_end_time_does_not_break_anything():
    no_end = vevent("No end", starts(2026, 10, 21, 9))
    [event] = upcoming(feed(no_end), NOW, NY)
    assert event.title == "No end"
    assert event.end >= event.start

# --------------------------------------------------------------------------
# Recurring events
# --------------------------------------------------------------------------
def test_a_daily_series_gives_one_event_per_day_at_the_right_local_time():
    standup = vevent(
        "Standup",
        starts(2026, 10, 15, 10),
        ends(2026, 10, 15, 10, 30),
        "RRULE:FREQ=DAILY",
    )
    result = upcoming(feed(standup), NOW, NY, limit=3)
    assert titles(result) == ["Standup"] * 3
    assert [(e.start.day, e.start.hour, e.start.minute) for e in result] == [
        (21, 10, 0), (22, 10, 0), (23, 10, 0),
    ]


def test_an_occurrence_that_already_ended_today_is_not_listed():
    standup = vevent("Standup", starts(2026, 10, 15, 10), ends(2026, 10, 15, 10, 30), "RRULE:FREQ=DAILY")
    first = upcoming(feed(standup), NOW, NY, limit=1)[0]
    assert first.start.day == 21


def test_a_series_that_never_ends_returns_the_default_five():
    forever = vevent("Forever", starts(2026, 1, 1, 8), ends(2026, 1, 1, 9), "RRULE:FREQ=DAILY")
    assert len(upcoming(feed(forever), NOW, NY)) == 5


def test_a_weekly_series_on_chosen_days():
    class_ = vevent(
        "Class",
        starts(2026, 10, 14, 9),
        ends(2026, 10, 14, 10),
        "RRULE:FREQ=WEEKLY;BYDAY=WE,FR",
    )
    result = upcoming(feed(class_), NOW, NY, limit=3)
    assert [(e.start.month, e.start.day) for e in result] == [(10, 21), (10, 23), (10, 28)]


def test_a_series_that_has_finished_gives_nothing():
    over = vevent("Over", starts(2026, 10, 10, 9), ends(2026, 10, 10, 10), "RRULE:FREQ=DAILY;COUNT=3")
    assert upcoming(feed(over), NOW, NY) == []


def test_a_cancelled_occurrence_is_left_out():
    class_ = vevent(
        "Class",
        starts(2026, 10, 14, 9),
        ends(2026, 10, 14, 10),
        "RRULE:FREQ=WEEKLY;BYDAY=WE",
        f"EXDATE:{utc_text(2026, 10, 21, 9)}",
    )
    result = upcoming(feed(class_), NOW, NY, limit=2)
    assert [(e.start.month, e.start.day) for e in result] == [(10, 28), (11, 4)]


def test_a_moved_occurrence_appears_only_at_its_new_time():
    # Google writes a recurring series with its own time zone, and a moved
    # occurrence points back at the original with RECURRENCE-ID in that same form.
    series = vevent(
        "Class",
        "DTSTART;TZID=America/New_York:20261014T090000",
        "DTEND;TZID=America/New_York:20261014T100000",
        "RRULE:FREQ=WEEKLY;BYDAY=WE",
        uid="class-series",
    )
    moved = vevent(
        "Class",
        "DTSTART;TZID=America/New_York:20261021T150000",
        "DTEND;TZID=America/New_York:20261021T160000",
        "RECURRENCE-ID;TZID=America/New_York:20261021T090000",
        uid="class-series",
    )
    result = upcoming(feed(series, moved), NOW, NY, limit=2)
    assert [(e.start.day, e.start.hour) for e in result] == [(21, 15), (28, 9)]


def test_a_series_with_its_own_zone_keeps_its_local_time_across_the_clock_change():
    # Clocks go back on 1 November: a 9:00 AM class stays at 9:00 AM local.
    class_ = vevent(
        "Class",
        "DTSTART;TZID=America/New_York:20261014T090000",
        "DTEND;TZID=America/New_York:20261014T100000",
        "RRULE:FREQ=WEEKLY;BYDAY=WE",
    )
    result = upcoming(feed(class_), NOW, NY, limit=3)
    assert [(e.start.month, e.start.day, e.start.hour) for e in result] == [
        (10, 21, 9), (10, 28, 9), (11, 4, 9),
    ]
    assert [e.start.utcoffset() for e in result] == [
        timedelta(hours=-4), timedelta(hours=-4), timedelta(hours=-5),
    ]


def test_a_series_and_one_off_events_are_merged_in_start_order():
    daily = vevent("Daily", starts(2026, 10, 15, 8), ends(2026, 10, 15, 9), "RRULE:FREQ=DAILY")
    calendar = feed(meeting("One-off", 10, 21, 8, 30), daily)
    assert titles(upcoming(calendar, NOW, NY, limit=3)) == ["Daily", "One-off", "Daily"]
