from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from agenda.models import Event
from agenda.views import agenda_rows

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=NY)


def timed(title, month, day, hour, minute=0, minutes=60):
    start = datetime(2026, month, day, hour, minute, tzinfo=NY)
    return Event(title, start, start + timedelta(minutes=minutes))


def all_day(title, month, day, days=1):
    start = datetime(2026, month, day, tzinfo=NY)
    return Event(title, start, start + timedelta(days=days), all_day=True)


def rows(*events):
    return agenda_rows(list(events), NOW, NY)


def test_a_row_is_day_then_time_then_title():
    assert rows(timed("Dentist", 10, 20, 15, 30)) == [["Today", "3:30 PM", "Dentist"]]


def test_an_all_day_event_has_all_day_as_its_time_cell():
    assert rows(all_day("Birthday", 10, 24)) == [["Sat", "All day", "Birthday"]]


def test_one_row_per_event_in_the_order_given():
    result = rows(timed("B", 10, 22, 9), timed("A", 10, 21, 9))
    assert result == [["Thu", "9:00 AM", "B"], ["Tomorrow", "9:00 AM", "A"]]


def test_every_row_has_exactly_three_cells():
    result = rows(timed("A", 10, 20, 9), all_day("B", 10, 24), timed("C", 11, 3, 9))
    assert {len(row) for row in result} == {3}


def test_cells_are_strings_without_surrounding_spaces():
    result = rows(timed("A", 10, 20, 9), all_day("B", 10, 24), timed("C", 11, 3, 9))
    for row in result:
        for cell in row:
            assert isinstance(cell, str)
            assert cell == cell.strip()


def test_no_events_gives_one_row_of_three_cells_saying_nothing_coming_up():
    assert agenda_rows([], NOW, NY) == [["Nothing coming up", "", ""]]


def test_a_long_title_is_kept_whole_in_the_title_cell():
    title = "Reservation: Mesa Tacos and Tequila with the whole department"
    assert rows(timed(title, 10, 21, 19)) == [["Tomorrow", "7:00 PM", title]]


def test_spaces_inside_a_title_are_kept():
    assert rows(timed("A  B", 10, 21, 9))[0][2] == "A  B"


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
def test_the_time_cell_is_twelve_hour_with_minutes_and_no_leading_zero(hour, minute, expected):
    assert rows(timed("X", 10, 21, hour, minute))[0][1] == expected


def test_today_and_tomorrow():
    result = rows(timed("A", 10, 20, 15), timed("B", 10, 21, 15))
    assert [row[0] for row in result] == ["Today", "Tomorrow"]


@pytest.mark.parametrize(
    "month, day, label",
    [(10, 22, "Thu"), (10, 23, "Fri"), (10, 26, "Mon")],
)
def test_within_a_week_the_day_cell_is_the_weekday(month, day, label):
    assert rows(timed("X", month, day, 9))[0][0] == label


@pytest.mark.parametrize(
    "month, day, label",
    [(10, 27, "Oct 27"), (11, 3, "Nov 3"), (11, 10, "Nov 10"), (11, 19, "Nov 19")],
)
def test_a_week_or_more_ahead_the_day_cell_is_month_and_day(month, day, label):
    assert rows(timed("X", month, day, 9))[0][0] == label


def test_the_day_cell_counts_calendar_days_not_24_hour_blocks():
    result = rows(timed("Late", 10, 20, 23, 30), timed("After midnight", 10, 21, 0, 30))
    assert [row[0] for row in result] == ["Today", "Tomorrow"]


def test_an_event_in_progress_is_labelled_today():
    assert rows(timed("Meeting", 10, 20, 11, minutes=120))[0][0] == "Today"


def test_a_running_multi_day_event_is_labelled_today():
    assert rows(all_day("Conference", 10, 19, days=3)) == [["Today", "All day", "Conference"]]


def test_a_start_given_in_utc_is_shown_in_the_display_zone():
    event = Event(
        "Call",
        datetime(2026, 10, 22, 14, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 22, 15, 30, tzinfo=timezone.utc),
    )
    assert rows(event) == [["Thu", "10:30 AM", "Call"]]


def test_the_day_cell_uses_the_local_date_not_the_utc_date():
    event = Event(
        "Late show",
        datetime(2026, 10, 21, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 21, 3, 30, tzinfo=timezone.utc),
    )
    assert rows(event) == [["Today", "10:30 PM", "Late show"]]


def test_a_month_and_day_label_uses_the_local_date_not_the_utc_date():
    event = Event(
        "Far away",
        datetime(2026, 11, 4, 2, 30, tzinfo=timezone.utc),
        datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc),
    )
    assert rows(event) == [["Nov 3", "9:30 PM", "Far away"]]


def test_today_is_worked_out_in_the_display_zone_even_if_now_is_in_utc():
    now_in_utc = datetime(2026, 10, 21, 2, 30, tzinfo=timezone.utc)
    result = agenda_rows([timed("Morning", 10, 21, 9)], now_in_utc, NY)
    assert result == [["Tomorrow", "9:00 AM", "Morning"]]


def test_today_comes_from_the_now_argument_not_the_machines_clock():
    march = datetime(2026, 3, 5, 12, 0, tzinfo=NY)
    start = datetime(2026, 3, 6, 9, 0, tzinfo=NY)
    event = Event("X", start, start + timedelta(hours=1))
    assert agenda_rows([event], march, NY) == [["Tomorrow", "9:00 AM", "X"]]


def test_a_now_without_a_time_zone_is_a_value_error():
    with pytest.raises(ValueError):
        agenda_rows([timed("A", 10, 21, 9)], datetime(2026, 10, 20, 12, 0), NY)


def test_a_now_without_a_time_zone_is_an_error_even_with_no_events():
    with pytest.raises(ValueError):
        agenda_rows([], datetime(2026, 10, 20, 12, 0), NY)


def test_the_input_list_is_left_alone():
    events = [timed("B", 10, 22, 9), timed("A", 10, 21, 9)]
    before = list(events)
    agenda_rows(events, NOW, NY)
    assert events == before


def test_rows_are_new_lists_on_every_call():
    events = [timed("A", 10, 21, 9)]
    first = agenda_rows(events, NOW, NY)
    first[0][2] = "changed"
    assert agenda_rows(events, NOW, NY)[0][2] == "A"
