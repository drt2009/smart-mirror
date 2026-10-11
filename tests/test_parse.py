"""Tests for weather.client.parse and the models in weather.models.

Contract
--------
parse(response) -> WeatherSnapshot

``response`` is what ``openmeteo.weather_api(...)[0]`` gives you. These tests
use a small fake that exposes the same methods you call on the real thing:

    response.Current().Variables(i).Value()
    response.Hourly().Variables(i).ValuesAsNumpy()
    response.Hourly().Time() / .TimeEnd() / .Interval()    (same for Daily())
    response.UtcOffsetSeconds()

models.py (all frozen dataclasses)
    CurrentWeather: temperature, feels_like, weather_code, condition
    HourlyEntry:    time, temperature, feels_like, precipitation_probability,
                    weather_code, condition
    DailyEntry:     date, high, low, precipitation_sum, weather_code, condition
    WeatherSnapshot: current, hourly, daily      (hourly/daily: list or tuple)

Rules the tests enforce
* Values are read through the Idx enums, never hardcoded positions.
* Numbers come out as plain Python float/int, not numpy types.
* Temperatures are NOT rounded here. Rounding is the view's job.
* ``condition`` is get_description(weather_code), resolved inside parse.
* Local times use the offset in the response, not a hardcoded timezone.
* The number of entries comes from the data, not from a hardcoded 4 or 3.
"""
import dataclasses
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest

from weather.client import parse
from weather.codes import get_description
from weather.models import (
    CurrentWeather,
    DailyEntry,
    HourlyEntry,
    WeatherSnapshot,
)
from weather.variables import CurrentIdx, DailyIdx, HourlyIdx

EDT = -4 * 3600
EST = -5 * 3600
BERLIN = 2 * 3600
DECOY = 1000.0  # unrequested slots get distinct junk so position bugs show up


def epoch(year, month, day, hour=0):
    return int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp())


def approx(value):
    # Values pass through float32, like the real SDK.
    return pytest.approx(value, rel=1e-5)


# --------------------------------------------------------------------------
# A fake of the Open-Meteo SDK response
# --------------------------------------------------------------------------
class FakeVariable:
    def __init__(self, values, length=1):
        array = np.asarray(values, dtype=np.float32)
        if array.ndim == 0:
            array = np.full(length, float(array), dtype=np.float32)
        self._values = array

    def Value(self):
        return float(self._values[0])

    def ValuesAsNumpy(self):
        return self._values


class FakeGroup:
    """Stands in for response.Current() / .Hourly() / .Daily()."""

    def __init__(self, variables, start=0, end=0, interval=0):
        self._variables = variables
        self._start = start
        self._end = end
        self._interval = interval

    def Variables(self, index):
        return self._variables[index]

    def Time(self):
        return self._start

    def TimeEnd(self):
        return self._end

    def Interval(self):
        return self._interval


class FakeResponse:
    def __init__(self, current, hourly, daily, utc_offset):
        self._current = current
        self._hourly = hourly
        self._daily = daily
        self._utc_offset = utc_offset

    def Current(self):
        return self._current

    def Hourly(self):
        return self._hourly

    def Daily(self):
        return self._daily

    def UtcOffsetSeconds(self):
        return self._utc_offset


def _variables(idx_enum, overrides, length):
    return [
        FakeVariable(overrides.get(member, DECOY + int(member)), length)
        for member in idx_enum
    ]


def make_response(
    *,
    current=None,
    hourly=None,
    daily=None,
    hours=4,
    days=3,
    utc_offset=EDT,
    hourly_start=None,
    daily_start=None,
):
    """Build a fake response. Slots you don't override get decoy values."""
    if hourly_start is None:
        hourly_start = epoch(2026, 10, 10, 22)  # 18:00 EDT
    if daily_start is None:
        daily_start = epoch(2026, 10, 10, 4)  # 00:00 EDT
    return FakeResponse(
        current=FakeGroup(_variables(CurrentIdx, current or {}, 1)),
        hourly=FakeGroup(
            _variables(HourlyIdx, hourly or {}, hours),
            hourly_start,
            hourly_start + hours * 3600,
            3600,
        ),
        daily=FakeGroup(
            _variables(DailyIdx, daily or {}, days),
            daily_start,
            daily_start + days * 86400,
            86400,
        ),
        utc_offset=utc_offset,
    )


SAMPLE_CURRENT = {
    CurrentIdx.TEMPERATURE_2M: 71.6,
    CurrentIdx.APPARENT_TEMPERATURE: 69.2,
    CurrentIdx.WEATHER_CODE: 3.0,
}
SAMPLE_HOURLY = {
    HourlyIdx.TEMPERATURE_2M: [70.1, 68.4, 66.0, 64.5],
    HourlyIdx.APPARENT_TEMPERATURE: [68.0, 66.5, 64.0, 62.5],
    HourlyIdx.WEATHER_CODE: [3.0, 61.0, 61.0, 0.0],
    HourlyIdx.PRECIPITATION_PROBABILITY: [10.0, 60.0, 70.0, 5.0],
}
SAMPLE_DAILY = {
    DailyIdx.TEMPERATURE_2M_MAX: [72.0, 65.0, 58.0],
    DailyIdx.TEMPERATURE_2M_MIN: [55.0, 50.0, 44.0],
    DailyIdx.WEATHER_CODE: [3.0, 61.0, 71.0],
    DailyIdx.PRECIPITATION_PROBABILITY_MEAN: [0.0, 10.0, 0.0],
}


@pytest.fixture
def snapshot():
    return parse(
        make_response(
            current=SAMPLE_CURRENT, hourly=SAMPLE_HOURLY, daily=SAMPLE_DAILY
        )
    )


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------
def test_returns_a_weather_snapshot(snapshot):
    assert isinstance(snapshot, WeatherSnapshot)
    assert isinstance(snapshot.current, CurrentWeather)
    assert isinstance(snapshot.hourly, (list, tuple))
    assert isinstance(snapshot.daily, (list, tuple))
    assert all(isinstance(entry, HourlyEntry) for entry in snapshot.hourly)
    assert all(isinstance(entry, DailyEntry) for entry in snapshot.daily)


MODEL_FIELDS = [
    pytest.param(
        CurrentWeather,
        {"temperature", "feels_like", "weather_code", "condition"},
        id="CurrentWeather",
    ),
    pytest.param(
        HourlyEntry,
        {
            "time",
            "temperature",
            "feels_like",
            "precipitation_probability",
            "weather_code",
            "condition",
        },
        id="HourlyEntry",
    ),
    pytest.param(
        DailyEntry,
        {"date", "high", "low", "precipitation_probability", "weather_code", "condition"},
        id="DailyEntry",
    ),
    pytest.param(
        WeatherSnapshot, {"current", "hourly", "daily"}, id="WeatherSnapshot"
    ),
]


@pytest.mark.parametrize("model, fields", MODEL_FIELDS)
def test_models_are_dataclasses_with_the_required_fields(model, fields):
    assert dataclasses.is_dataclass(model)
    assert fields <= {f.name for f in dataclasses.fields(model)}


def test_parsed_objects_are_immutable(snapshot):
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.current.temperature = 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.hourly[0].temperature = 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.daily[0].high = 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.current = None


# --------------------------------------------------------------------------
# Current
# --------------------------------------------------------------------------
def test_current_values(snapshot):
    current = snapshot.current
    assert current.temperature == approx(71.6)
    assert current.feels_like == approx(69.2)
    assert current.weather_code == 3


def test_current_condition_is_resolved_from_the_code(snapshot):
    assert snapshot.current.condition == get_description(3)


def test_current_uses_plain_python_types(snapshot):
    assert type(snapshot.current.temperature) is float
    assert type(snapshot.current.feels_like) is float
    assert type(snapshot.current.weather_code) is int


def test_current_temperature_is_not_rounded(snapshot):
    assert snapshot.current.temperature != round(snapshot.current.temperature)


def test_unknown_weather_code_falls_back_instead_of_crashing():
    snap = parse(make_response(current={CurrentIdx.WEATHER_CODE: 999.0}))
    assert snap.current.condition == get_description(-1)


# --------------------------------------------------------------------------
# Hourly
# --------------------------------------------------------------------------
def test_hourly_values_are_in_order(snapshot):
    hourly = snapshot.hourly
    assert [h.temperature for h in hourly] == approx([70.1, 68.4, 66.0, 64.5])
    assert [h.feels_like for h in hourly] == approx([68.0, 66.5, 64.0, 62.5])
    assert [h.precipitation_probability for h in hourly] == approx(
        [10.0, 60.0, 70.0, 5.0]
    )
    assert [h.weather_code for h in hourly] == [3, 61, 61, 0]


def test_hourly_conditions_come_from_each_entrys_own_code(snapshot):
    assert [h.condition for h in snapshot.hourly] == [
        get_description(3),
        get_description(61),
        get_description(61),
        get_description(0),
    ]


def test_hourly_uses_plain_python_types(snapshot):
    entry = snapshot.hourly[0]
    assert type(entry.temperature) is float
    assert type(entry.feels_like) is float
    assert type(entry.precipitation_probability) is float
    assert type(entry.weather_code) is int


def test_hourly_times_are_local_and_one_hour_apart(snapshot):
    times = [h.time for h in snapshot.hourly]
    assert all(isinstance(t, datetime) for t in times)
    assert times[0].date() == date(2026, 10, 10)
    assert times[0].hour == 18
    assert times[0].utcoffset() == timedelta(seconds=EDT)
    assert [b - a for a, b in zip(times, times[1:])] == [timedelta(hours=1)] * 3


# --------------------------------------------------------------------------
# Daily
# --------------------------------------------------------------------------
def test_daily_values_are_in_order(snapshot):
    daily = snapshot.daily
    assert [d.high for d in daily] == approx([72.0, 65.0, 58.0])
    assert [d.low for d in daily] == approx([55.0, 50.0, 44.0])
    assert [d.precipitation_sum for d in daily] == approx([0.0, 0.4, 0.0])
    assert [d.weather_code for d in daily] == [3, 61, 71]


def test_daily_conditions_come_from_each_entrys_own_code(snapshot):
    assert [d.condition for d in snapshot.daily] == [
        get_description(3),
        get_description(61),
        get_description(71),
    ]


def test_daily_dates_are_consecutive_local_dates(snapshot):
    assert [d.date for d in snapshot.daily] == [
        date(2026, 10, 10),
        date(2026, 10, 11),
        date(2026, 10, 12),
    ]
    assert all(type(d.date) is date for d in snapshot.daily)


def test_daily_uses_plain_python_types(snapshot):
    entry = snapshot.daily[0]
    assert type(entry.high) is float
    assert type(entry.low) is float
    assert type(entry.precipitation_sum) is float
    assert type(entry.weather_code) is int


# --------------------------------------------------------------------------
# Counts and timezones
# --------------------------------------------------------------------------
@pytest.mark.parametrize("hours, days", [(1, 1), (4, 3), (24, 7)])
def test_entry_counts_follow_the_data(hours, days):
    snap = parse(make_response(hours=hours, days=days))
    assert len(snap.hourly) == hours
    assert len(snap.daily) == days


def test_local_time_uses_the_offset_in_the_response_est():
    snap = parse(
        make_response(
            utc_offset=EST,
            hourly_start=epoch(2026, 11, 10, 23),  # 18:00 EST
            daily_start=epoch(2026, 11, 10, 5),  # 00:00 EST
        )
    )
    assert snap.hourly[0].time.date() == date(2026, 11, 10)
    assert snap.hourly[0].time.hour == 18
    assert snap.daily[0].date == date(2026, 11, 10)


def test_positive_offsets_roll_the_local_date_forward():
    # Local midnight on Oct 10 at UTC+2 is 22:00 UTC on Oct 9. A parser that
    # ignores the offset gets the wrong date here.
    snap = parse(
        make_response(
            utc_offset=BERLIN,
            hourly_start=epoch(2026, 10, 9, 22),
            daily_start=epoch(2026, 10, 9, 22),
        )
    )
    assert snap.hourly[0].time.date() == date(2026, 10, 10)
    assert snap.hourly[0].time.hour == 0
    assert snap.daily[0].date == date(2026, 10, 10)


# --------------------------------------------------------------------------
# Reading by name, not by position
# --------------------------------------------------------------------------
def test_values_are_read_by_variable_not_by_position():
    # Every slot holds junk except the ones we set, so a hardcoded index
    # would pick up a decoy and fail.
    snap = parse(
        make_response(
            current={
                CurrentIdx.TEMPERATURE_2M: 50.0,
                CurrentIdx.APPARENT_TEMPERATURE: 45.0,
                CurrentIdx.WEATHER_CODE: 0.0,
            }
        )
    )
    assert snap.current.temperature == approx(50.0)
    assert snap.current.feels_like == approx(45.0)
    assert snap.current.weather_code == 0