from datetime import date, datetime, timedelta, timezone

import pytest

from weather.models import CurrentWeather, DailyEntry, HourlyEntry, WeatherSnapshot
from weather.views import daily_rows, hourly_rows

EDT = timezone(timedelta(hours=-4))
TODAY = date(2026, 10, 10)


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


def one_hour(**changes):
    values = dict(
        time=datetime(2026, 10, 10, 18, tzinfo=EDT),
        temperature=70.0,
        feels_like=68.0,
        precipitation_probability=0.0,
        weather_code=0,
        condition="Clear sky",
    )
    values.update(changes)
    return HourlyEntry(**values)


def one_day(**changes):
    values = dict(
        date=date(2026, 10, 10),
        high=70.0,
        low=50.0,
        precipitation_probability=0.0,
        weather_code=0,
        condition="Clear sky",
    )
    values.update(changes)
    return DailyEntry(**values)


# --------------------------------------------------------------------------
# hourly_rows
# --------------------------------------------------------------------------
def test_hourly_rows_are_the_cells_of_each_entry_in_order():
    assert hourly_rows(make_snapshot()) == [
        ["6 PM", "70°", "Overcast", ""],
        ["7 PM", "68°", "Slight rain", "60%"],
        ["8 PM", "66°", "Slight rain", "70%"],
        ["9 PM", "64°", "Clear sky", ""],
    ]


def test_every_hourly_row_has_the_same_number_of_cells():
    rows = hourly_rows(make_snapshot())
    assert {len(row) for row in rows} == {4}


def test_a_hidden_hourly_chance_is_an_empty_cell_not_a_missing_one():
    row = hourly_rows(make_snapshot(hourly=[one_hour(precipitation_probability=5.0)]))[0]
    assert len(row) == 4
    assert row[3] == ""


def test_the_hourly_chance_is_the_last_cell():
    row = hourly_rows(make_snapshot(hourly=[one_hour(precipitation_probability=60.0)]))[0]
    assert row[3] == "60%"
    assert row[2] == "Clear sky"


def test_hourly_cells_are_strings():
    for row in hourly_rows(make_snapshot()):
        assert all(isinstance(cell, str) for cell in row)


def test_hourly_rows_follow_the_data_size():
    assert len(hourly_rows(make_snapshot(hourly=[one_hour()]))) == 1
    assert hourly_rows(make_snapshot(hourly=[])) == []


# --------------------------------------------------------------------------
# daily_rows
# --------------------------------------------------------------------------
def test_daily_rows_are_the_cells_of_each_entry_in_order():
    assert daily_rows(make_snapshot(), today=TODAY) == [
        ["Today", "72°", "55°", "Overcast", ""],
        ["Sun", "65°", "50°", "Slight rain", "80%"],
        ["Mon", "58°", "44°", "Slight snowfall", ""],
    ]


def test_every_daily_row_has_the_same_number_of_cells():
    rows = daily_rows(make_snapshot(), today=TODAY)
    assert {len(row) for row in rows} == {5}


def test_a_hidden_daily_chance_is_an_empty_cell_not_a_missing_one():
    row = daily_rows(make_snapshot(daily=[one_day(precipitation_probability=15.0)]), today=TODAY)[0]
    assert len(row) == 5
    assert row[4] == ""


def test_the_daily_high_comes_before_the_low():
    row = daily_rows(make_snapshot(daily=[one_day(high=61.0, low=42.0)]), today=TODAY)[0]
    assert row[1] == "61°"
    assert row[2] == "42°"


def test_daily_labels_depend_on_the_given_today():
    rows = daily_rows(make_snapshot(), today=date(2026, 10, 11))
    assert rows[0][0] == "Sat"
    assert rows[1][0] == "Today"


def test_daily_cells_are_strings():
    for row in daily_rows(make_snapshot(), today=TODAY):
        assert all(isinstance(cell, str) for cell in row)


def test_daily_rows_handle_empty_data():
    assert daily_rows(make_snapshot(daily=[]), today=TODAY) == []


# --------------------------------------------------------------------------
# No side effects, rows are independent
# --------------------------------------------------------------------------
def test_row_builders_do_not_change_the_snapshot():
    snap = make_snapshot()
    before = make_snapshot()
    hourly_rows(snap)
    daily_rows(snap, today=TODAY)
    assert snap == before


def test_rows_are_new_lists_on_every_call():
    snap = make_snapshot()
    first = hourly_rows(snap)
    first[0][0] = "changed"
    assert hourly_rows(snap)[0][0] == "6 PM"
