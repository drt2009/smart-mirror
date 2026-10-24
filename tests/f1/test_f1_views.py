"""Pure display functions: f1/views.py.

No tkinter, no network, and NO clock: ``now`` and ``tz`` are always passed in.
All datetimes are timezone-aware. A date is always decided in ``tz`` (the mirror's
local zone), never in UTC and never in the machine's zone.

Contract
--------
format_time(moment, tz) -> str
    12-hour clock in tz, no leading zero: "3:00 PM", "12:05 PM", "12:00 AM", "9:00 AM".

format_day(moment, now, tz) -> str      (both dates taken in tz)
    same day as now         "Today"
    the next day            "Tomorrow"
    2 to 6 days ahead       weekday abbreviation: "Sun"
    7 or more days ahead    month abbreviation and day without a zero: "Nov 8", "Dec 15"

format_when(moment, now, tz) -> str
    "<day> <time>" with a single space and NO trailing space: "Tomorrow 3:00 PM".

upcoming_race_view(race, now, tz) -> list[str]
    [ race_name,                         "Miami Grand Prix"
      "<circuit_name>, <country>",       "Miami International Autodrome, USA"
      format_when(race_date, now, tz) ]  "Sun 3:00 PM"
    plus a fourth line "Sprint weekend" ONLY when race.sprint_race is True.

f1_lines(state, now, tz) -> list[str]
    state still loading, no failure          ["Loading..."]
    state still loading, last fetch failed   one line, not "Loading..."  (F1 unavailable)
    state loaded with no race (season over)  one line, not "Loading..."
    state with a race                        upcoming_race_view(state.race, now, tz),
                                             even when the last fetch failed or the
                                             data is stale (old data beats a blank)
    The state is only read, never changed.
"""
from datetime import datetime, timedelta, timezone

import pytest

from f1.models import UpcomingRace
from f1.state import F1State
from f1.views import (
    f1_lines,
    format_day,
    format_time,
    format_when,
    upcoming_race_view,
)

UTC = timezone.utc
EST = timezone(timedelta(hours=-5))
TOKYO = timezone(timedelta(hours=9))

SUNDAY_RACE = datetime(2026, 11, 8, 20, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 4, 17, 0, tzinfo=UTC)


def make_race(race_date=SUNDAY_RACE, sprint=False, name="Miami Grand Prix"):
    return UpcomingRace(
        race_name=name,
        circuit_name="Miami International Autodrome",
        country="USA",
        race_date=race_date,
        sprint_race=sprint,
    )


def loaded_state(race):
    state = F1State(600)
    state.update(race)
    return state


class TestFormatTime:
    @pytest.mark.parametrize("hour, minute, expected", [
        (20, 0, "3:00 PM"),
        (17, 5, "12:05 PM"),
        (5, 0, "12:00 AM"),
        (14, 0, "9:00 AM"),
        (4, 59, "11:59 PM"),
        (23, 30, "6:30 PM"),
    ])
    def test_it_is_a_twelve_hour_clock_without_a_leading_zero(self, hour, minute, expected):
        moment = datetime(2026, 11, 8, hour, minute, tzinfo=UTC)
        assert format_time(moment, EST) == expected

    def test_the_zone_decides_the_hour(self):
        assert format_time(SUNDAY_RACE, TOKYO) == "5:00 AM"

    def test_a_moment_in_another_zone_is_converted(self):
        moment = SUNDAY_RACE.astimezone(TOKYO)
        assert format_time(moment, EST) == "3:00 PM"


class TestFormatDay:
    def test_the_same_day_is_today(self):
        now = datetime(2026, 11, 8, 14, 0, tzinfo=UTC)
        assert format_day(SUNDAY_RACE, now, EST) == "Today"

    def test_the_next_day_is_tomorrow(self):
        now = datetime(2026, 11, 7, 14, 0, tzinfo=UTC)
        assert format_day(SUNDAY_RACE, now, EST) == "Tomorrow"

    def test_two_to_six_days_ahead_is_the_weekday(self):
        for days in range(2, 7):
            now = SUNDAY_RACE - timedelta(days=days)
            assert format_day(SUNDAY_RACE, now, EST) == "Sun", days

    def test_seven_days_ahead_is_month_and_day(self):
        now = SUNDAY_RACE - timedelta(days=7)
        assert format_day(SUNDAY_RACE, now, EST) == "Nov 8"

    def test_the_day_has_no_leading_zero(self):
        race = datetime(2026, 11, 9, 20, 0, tzinfo=UTC)
        now = race - timedelta(days=10)
        assert format_day(race, now, EST) == "Nov 9"

    def test_a_two_digit_day_is_kept_whole(self):
        race = datetime(2026, 12, 15, 20, 0, tzinfo=UTC)
        now = race - timedelta(days=30)
        assert format_day(race, now, EST) == "Dec 15"

    def test_the_weekday_is_the_local_weekday(self):
        race = datetime(2026, 11, 9, 2, 0, tzinfo=UTC)
        now = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
        assert format_day(race, now, EST) == "Sun"

    def test_a_race_on_the_utc_next_day_can_still_be_today_locally(self):
        race = datetime(2026, 11, 8, 2, 0, tzinfo=UTC)
        now = datetime(2026, 11, 7, 20, 0, tzinfo=UTC)
        assert format_day(race, now, EST) == "Today"

    def test_now_late_in_the_evening_locally_but_tomorrow_in_utc(self):
        now = datetime(2026, 11, 8, 2, 0, tzinfo=UTC)
        race = datetime(2026, 11, 8, 20, 0, tzinfo=UTC)
        assert format_day(race, now, EST) == "Tomorrow"

    def test_the_month_and_day_use_the_local_date(self):
        race = datetime(2026, 12, 1, 2, 0, tzinfo=UTC)
        now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        assert format_day(race, now, EST) == "Nov 30"

    def test_a_moment_in_another_zone_is_converted_before_the_date_is_taken(self):
        race = SUNDAY_RACE.astimezone(TOKYO)
        now = NOW.astimezone(TOKYO)
        assert format_day(race, now, EST) == "Sun"

    def test_across_a_daylight_saving_change(self):
        zoneinfo = pytest.importorskip("zoneinfo")
        try:
            ny = zoneinfo.ZoneInfo("America/New_York")
        except zoneinfo.ZoneInfoNotFoundError:
            pytest.skip("no time zone database; pip install tzdata")
        race = datetime(2026, 11, 2, 6, 0, tzinfo=UTC)
        now = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
        assert format_day(race, now, ny) == "Tomorrow"
        assert format_time(race, ny) == "1:00 AM"


class TestFormatWhen:
    def test_day_and_time_are_joined_by_one_space(self):
        now = datetime(2026, 11, 7, 14, 0, tzinfo=UTC)
        assert format_when(SUNDAY_RACE, now, EST) == "Tomorrow 3:00 PM"

    def test_there_is_no_trailing_or_leading_space(self):
        text = format_when(SUNDAY_RACE, NOW, EST)
        assert text == text.strip()

    def test_a_weekday_example(self):
        assert format_when(SUNDAY_RACE, NOW, EST) == "Sun 3:00 PM"

    def test_a_far_away_example(self):
        now = SUNDAY_RACE - timedelta(days=30)
        assert format_when(SUNDAY_RACE, now, EST) == "Nov 8 3:00 PM"


class TestUpcomingRaceView:
    def test_a_normal_weekend_is_three_lines(self):
        assert upcoming_race_view(make_race(), NOW, EST) == [
            "Miami Grand Prix",
            "Miami International Autodrome, USA",
            "Sun 3:00 PM",
        ]

    def test_the_grand_prix_name_is_the_first_line(self):
        lines = upcoming_race_view(make_race(name="Monaco Grand Prix"), NOW, EST)
        assert lines[0] == "Monaco Grand Prix"

    def test_a_sprint_weekend_gets_a_fourth_line(self):
        lines = upcoming_race_view(make_race(sprint=True), NOW, EST)
        assert lines == [
            "Miami Grand Prix",
            "Miami International Autodrome, USA",
            "Sun 3:00 PM",
            "Sprint weekend",
        ]

    def test_the_time_is_shown_in_the_given_zone(self):
        lines = upcoming_race_view(make_race(), NOW, TOKYO)
        assert lines[2] == "Mon 5:00 AM"

    def test_the_view_depends_on_the_now_it_is_given(self):
        today = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
        assert upcoming_race_view(make_race(), today, EST)[2] == "Today 3:00 PM"

    def test_it_returns_a_new_list_each_time(self):
        race = make_race()
        first = upcoming_race_view(race, NOW, EST)
        first.append("junk")
        assert len(upcoming_race_view(race, NOW, EST)) == 3


class TestF1Lines:
    def test_while_loading_it_says_so(self):
        assert f1_lines(F1State(600), NOW, EST) == ["Loading..."]

    def test_a_failure_before_any_data_is_not_shown_as_loading(self):
        state = F1State(600)
        state.mark_failed()
        lines = f1_lines(state, NOW, EST)
        assert len(lines) == 1
        assert lines[0].strip()
        assert lines != ["Loading..."]

    def test_a_finished_season_is_its_own_message(self):
        state = loaded_state(None)
        lines = f1_lines(state, NOW, EST)
        failed = F1State(600)
        failed.mark_failed()
        assert len(lines) == 1
        assert lines[0].strip()
        assert lines != ["Loading..."]
        assert lines != f1_lines(failed, NOW, EST)

    def test_a_loaded_race_shows_the_race(self):
        state = loaded_state(make_race())
        assert f1_lines(state, NOW, EST) == upcoming_race_view(make_race(), NOW, EST)

    def test_a_failure_after_data_keeps_showing_the_old_race(self):
        state = loaded_state(make_race())
        state.mark_failed()
        assert f1_lines(state, NOW, EST) == upcoming_race_view(make_race(), NOW, EST)

    def test_stale_data_is_still_shown(self):
        ticks = [0.0]
        state = F1State(10, clock=lambda: ticks[0])
        state.update(make_race())
        ticks[0] = 1000.0
        assert state.is_stale
        assert f1_lines(state, NOW, EST) == upcoming_race_view(make_race(), NOW, EST)

    def test_the_state_is_not_changed_by_looking_at_it(self):
        state = loaded_state(make_race())
        state.mark_failed()
        f1_lines(state, NOW, EST)
        assert state.last_fetch_failed is True
        assert state.race == make_race()
        assert state.is_loading is False

    def test_looking_at_a_healthy_state_does_not_mark_it_failed(self):
        state = loaded_state(make_race())
        f1_lines(state, NOW, EST)
        assert state.last_fetch_failed is False

    def test_the_lines_follow_the_now_it_is_given(self):
        state = loaded_state(make_race())
        today = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
        assert f1_lines(state, today, EST)[2] == "Today 3:00 PM"
