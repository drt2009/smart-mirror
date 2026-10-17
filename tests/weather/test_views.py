"""Tests for weather/views.py: turning a WeatherSnapshot into display text.

Everything here is a pure function: no tkinter, no network, no clock.

Contract
--------
format_temperature(value: float) -> str
    Rounded to a whole degree with a degree sign: 71.6 -> "72°".
    Never "-0°": -0.4 -> "0°".

format_hour(moment: datetime) -> str
    12-hour clock, no leading zero, no minutes, uses the datetime's own
    (already local) hour: 18:00 -> "6 PM", 0:00 -> "12 AM", 12:00 -> "12 PM".

format_day(day: date, today: date) -> str
    "Today" when day == today, otherwise the English weekday abbreviation
    ("Mon", "Tue", ...).

format_chance(percent: float) -> str
    "" when the chance is below 20 (not worth showing), otherwise the rounded
    percentage: 60.0 -> "60%". The threshold applies to the raw value.

current_view(snapshot)  -> list[str]
    Exactly three lines: temperature, condition, "Feels like <temp>".

hourly_view(snapshot)   -> list[str]
    One line per hourly entry, in order. Each line contains, left to right:
    the hour, the temperature, the condition, and (only when worth showing)
    the chance of rain.

daily_view(snapshot, today: date) -> list[str]
    One line per daily entry, in order. Each line contains, left to right:
    the day label, the high, the low, the condition, and (only when worth
    showing) the chance of rain.

Empty hourly/daily data gives an empty list. Views never change the snapshot.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from weather.models import CurrentWeather, DailyEntry, HourlyEntry, WeatherSnapshot
from weather.views import (
    current_view,
    daily_view,
    format_chance,
    format_day,
    format_hour,
    format_temperature,
    hourly_view,
)

EDT = timezone(timedelta(hours=-4))
TODAY = date(2026, 10, 10)  # a Saturday


def make_snapshot(hourly=None, daily=None):
    return WeatherSnapshot(
        current=CurrentWeather(
            temperature=71.6, feels_like=69.2, weather_code=3, condition="Overcast"
        ),
        hourly=tuple(
            hourly
            if hourly is not None
            else [
                HourlyEntry(
                    time=datetime(2026, 10, 10, 18 + i, tzinfo=EDT),
                    temperature=t,
                    feels_like=t - 2,
                    precipitation_probability=p,
                    weather_code=code,
                    condition=cond,
                )
                for i, (t, p, code, cond) in enumerate(
                    [
                        (70.1, 10.0, 3, "Overcast"),
                        (68.4, 60.0, 61, "Slight rain"),
                        (66.0, 70.0, 61, "Slight rain"),
                        (64.5, 5.0, 0, "Clear sky"),
                    ]
                )
            ]
        ),
        daily=tuple(
            daily
            if daily is not None
            else [
                DailyEntry(
                    date=date(2026, 10, 10) + timedelta(days=i),
                    high=h,
                    low=lo,
                    precipitation_probability=p,
                    weather_code=code,
                    condition=cond,
                )
                for i, (h, lo, p, code, cond) in enumerate(
                    [
                        (72.0, 55.0, 15.0, 3, "Overcast"),
                        (65.0, 50.0, 80.0, 61, "Slight rain"),
                        (58.0, 44.0, 0.0, 71, "Slight snowfall"),
                    ]
                )
            ]
        ),
    )


# --------------------------------------------------------------------------
# format_temperature
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value, expected",
    [
        (71.6, "72°"),
        (71.4, "71°"),
        (72.0, "72°"),
        (0.0, "0°"),
        (-0.4, "0°"),
        (-3.6, "-4°"),
        (-12.2, "-12°"),
        (100.0, "100°"),
    ],
)
def test_format_temperature(value, expected):
    assert format_temperature(value) == expected


# --------------------------------------------------------------------------
# format_hour
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "hour, expected",
    [
        (0, "12 AM"),
        (1, "1 AM"),
        (9, "9 AM"),
        (11, "11 AM"),
        (12, "12 PM"),
        (13, "1 PM"),
        (18, "6 PM"),
        (23, "11 PM"),
    ],
)
def test_format_hour(hour, expected):
    assert format_hour(datetime(2026, 10, 10, hour, tzinfo=EDT)) == expected


def test_format_hour_ignores_minutes():
    assert format_hour(datetime(2026, 10, 10, 18, 45, tzinfo=EDT)) == "6 PM"


def test_format_hour_uses_the_datetimes_own_hour_without_converting():
    utc_midnight = datetime(2026, 10, 10, 0, tzinfo=timezone.utc)
    assert format_hour(utc_midnight) == "12 AM"


# --------------------------------------------------------------------------
# format_day
# --------------------------------------------------------------------------
def test_today_is_labelled_today():
    assert format_day(TODAY, today=TODAY) == "Today"


@pytest.mark.parametrize(
    "offset, expected",
    [(1, "Sun"), (2, "Mon"), (3, "Tue"), (4, "Wed"), (5, "Thu"), (6, "Fri"), (7, "Sat")],
)
def test_other_days_use_the_weekday_abbreviation(offset, expected):
    assert format_day(TODAY + timedelta(days=offset), today=TODAY) == expected


# --------------------------------------------------------------------------
# format_chance
# --------------------------------------------------------------------------
@pytest.mark.parametrize("percent", [0.0, 5.0, 10.0, 19.0])
def test_low_chances_are_hidden(percent):
    assert format_chance(percent) == ""


@pytest.mark.parametrize(
    "percent, expected",
    [(20.0, "20%"), (60.0, "60%"), (59.6, "60%"), (100.0, "100%")],
)
def test_worthwhile_chances_are_shown_rounded(percent, expected):
    assert format_chance(percent) == expected


# --------------------------------------------------------------------------
# current_view
# --------------------------------------------------------------------------
def test_current_view_has_three_lines():
    assert current_view(make_snapshot()) == ["72°", "Overcast", "Feels like 69°"]


def test_current_view_rounds_each_value_on_its_own():
    snap = WeatherSnapshot(
        current=CurrentWeather(
            temperature=-0.4, feels_like=-3.6, weather_code=0, condition="Clear sky"
        ),
        hourly=(),
        daily=(),
    )
    assert current_view(snap) == ["0°", "Clear sky", "Feels like -4°"]


# --------------------------------------------------------------------------
# hourly_view
# --------------------------------------------------------------------------
def test_hourly_view_has_one_line_per_entry_in_order():
    lines = hourly_view(make_snapshot())
    assert len(lines) == 4
    assert [line.split()[0] for line in lines] == ["6", "7", "8", "9"]
    assert all("PM" in line for line in lines)


def test_hourly_line_order_is_hour_then_temperature_then_condition():
    line = hourly_view(make_snapshot())[0]
    assert line.startswith("6 PM")
    assert line.index("6 PM") < line.index("70°") < line.index("Overcast")


def test_hourly_line_hides_a_low_chance():
    line = hourly_view(make_snapshot())[0]  # 10%
    assert "%" not in line


def test_hourly_line_shows_a_worthwhile_chance_after_the_condition():
    line = hourly_view(make_snapshot())[1]  # 60%
    assert "Slight rain" in line
    assert line.index("Slight rain") < line.index("60%")


def test_hourly_view_follows_the_data_size():
    one = make_snapshot(
        hourly=[
            HourlyEntry(
                time=datetime(2026, 10, 10, 18, tzinfo=EDT),
                temperature=70.0,
                feels_like=68.0,
                precipitation_probability=0.0,
                weather_code=0,
                condition="Clear sky",
            )
        ]
    )
    assert len(hourly_view(one)) == 1
    assert hourly_view(make_snapshot(hourly=[])) == []


# --------------------------------------------------------------------------
# daily_view
# --------------------------------------------------------------------------
def test_daily_view_has_one_line_per_entry_in_order():
    lines = daily_view(make_snapshot(), today=TODAY)
    assert len(lines) == 3
    assert lines[0].startswith("Today")
    assert lines[1].startswith("Sun")
    assert lines[2].startswith("Mon")


def test_daily_line_order_is_day_high_low_condition():
    line = daily_view(make_snapshot(), today=TODAY)[0]
    assert line.index("Today") < line.index("72°") < line.index("55°")
    assert line.index("55°") < line.index("Overcast")


def test_daily_line_hides_a_low_chance_and_shows_a_high_one():
    lines = daily_view(make_snapshot(), today=TODAY)
    assert "%" not in lines[0]  # 15%
    assert "80%" in lines[1]
    assert "%" not in lines[2]  # 0%


def test_daily_labels_depend_on_the_given_today():
    lines = daily_view(make_snapshot(), today=date(2026, 10, 11))
    assert lines[0].startswith("Sat")  # yesterday relative to that "today"
    assert lines[1].startswith("Today")


def test_daily_view_handles_empty_data():
    assert daily_view(make_snapshot(daily=[]), today=TODAY) == []


# --------------------------------------------------------------------------
# No side effects
# --------------------------------------------------------------------------
def test_views_do_not_change_the_snapshot():
    snap = make_snapshot()
    before = make_snapshot()
    current_view(snap)
    hourly_view(snap)
    daily_view(snap, today=TODAY)
    assert snap == before
