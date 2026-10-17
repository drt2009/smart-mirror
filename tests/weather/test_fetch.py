"""Tests for fetch_weather in weather/client.py.

Contract
--------
weather/client.py defines

    class WeatherFetchError(Exception)
    def _get_client()                    # builds the Open-Meteo SDK client
    def fetch_weather(lat, lon)          # -> WeatherSnapshot

* fetch_weather builds its client by calling the module-level ``_get_client()``
  (never at import time) and turns the response into a snapshot by calling the
  module-level ``parse``. Both names are looked up when the function runs, so
  the tests can swap them for fakes. No test here touches the network.
* One call to ``client.weather_api(url, params, ...)``.
    url      https://api.open-meteo.com/v1/forecast
    params   latitude, longitude          exactly as passed in
             current / hourly / daily     the lists from weather.variables
                                          (a list, tuple or comma-joined string)
             forecast_hours = 4, forecast_days = 3
             temperature_unit = fahrenheit, wind_speed_unit = mph,
             precipitation_unit = inch
             timezone = auto
    kwargs   timeout = a positive number (or a tuple of them)
* The first response in the returned list is the one that gets parsed.
* ANY failure (client raising, empty response list, parse raising) is raised as
  WeatherFetchError with the original exception chained as __cause__.
"""
import math

import pytest

import weather.client as client
from weather.client import WeatherFetchError, fetch_weather
from weather.variables import CURRENT, DAILY, HOURLY

try:  # name used by recent versions of the SDK
    from openmeteo_requests import OpenMeteoRequestsError
except ImportError:  # pragma: no cover
    class OpenMeteoRequestsError(Exception):
        pass

LAT, LON = 42.475136, -83.221275
SNAPSHOT = object()
URL = "https://api.open-meteo.com/v1/forecast"


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = responses if responses is not None else ["first"]
        self.error = error
        self.calls = []

    def weather_api(self, url, params, *args, **kwargs):
        self.calls.append((url, dict(params), kwargs))
        if self.error is not None:
            raise self.error
        return self.responses


@pytest.fixture
def setup(monkeypatch):
    """Install a fake SDK client and a recording fake for parse."""

    def _setup(responses=None, error=None, parse_error=None):
        fake = FakeClient(responses, error)
        parsed = []

        def fake_parse(response):
            parsed.append(response)
            if parse_error is not None:
                raise parse_error
            return SNAPSHOT

        monkeypatch.setattr(client, "_get_client", lambda: fake)
        monkeypatch.setattr(client, "parse", fake_parse)
        return fake, parsed

    return _setup


def as_list(value):
    if isinstance(value, str):
        return value.split(",")
    return list(value)


def request_of(fake):
    assert len(fake.calls) == 1, "expected exactly one API call"
    return fake.calls[0]


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------
def test_returns_what_parse_returns(setup):
    setup()
    assert fetch_weather(LAT, LON) is SNAPSHOT


def test_only_the_first_response_is_parsed(setup):
    _, parsed = setup(responses=["first", "second"])
    fetch_weather(LAT, LON)
    assert parsed == ["first"]


def test_makes_exactly_one_api_call(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    assert len(fake.calls) == 1


# --------------------------------------------------------------------------
# Request
# --------------------------------------------------------------------------
def test_uses_the_forecast_endpoint(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    url, _, _ = request_of(fake)
    assert url == URL


def test_coordinates_are_passed_through_unchanged(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, params, _ = request_of(fake)
    assert params["latitude"] == LAT
    assert params["longitude"] == LON


def test_other_coordinates_are_not_hardcoded(setup):
    fake, _ = setup()
    fetch_weather(-33.8688, 151.2093)
    _, params, _ = request_of(fake)
    assert params["latitude"] == -33.8688
    assert params["longitude"] == 151.2093


@pytest.mark.parametrize(
    "key, names",
    [("current", CURRENT), ("hourly", HOURLY), ("daily", DAILY)],
)
def test_requests_the_variables_from_variables_py(setup, key, names):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, params, _ = request_of(fake)
    assert as_list(params[key]) == list(names)


def test_requests_four_hours_and_three_days(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, params, _ = request_of(fake)
    assert params["forecast_hours"] == 4
    assert params["forecast_days"] == 3


@pytest.mark.parametrize(
    "key, value",
    [
        ("temperature_unit", "fahrenheit"),
        ("wind_speed_unit", "mph"),
        ("precipitation_unit", "inch"),
    ],
)
def test_units_are_set_explicitly(setup, key, value):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, params, _ = request_of(fake)
    assert params[key] == value


def test_timezone_is_auto(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, params, _ = request_of(fake)
    assert params["timezone"] == "auto"


def test_a_timeout_is_set(setup):
    fake, _ = setup()
    fetch_weather(LAT, LON)
    _, _, kwargs = request_of(fake)
    timeout = kwargs.get("timeout")
    assert timeout is not None, "pass timeout=... to weather_api"
    values = timeout if isinstance(timeout, tuple) else (timeout,)
    assert all(
        isinstance(v, (int, float)) and 0 < v < math.inf for v in values
    )


# --------------------------------------------------------------------------
# Failure handling
# --------------------------------------------------------------------------
def test_error_type_is_a_normal_exception():
    assert issubclass(WeatherFetchError, Exception)


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("no network"),
        TimeoutError("timed out"),
        OpenMeteoRequestsError("failed to request"),
        RuntimeError("anything else"),
    ],
    ids=["connection", "timeout", "sdk", "other"],
)
def test_client_failures_become_weather_fetch_error(setup, error):
    setup(error=error)
    with pytest.raises(WeatherFetchError) as info:
        fetch_weather(LAT, LON)
    assert info.value.__cause__ is error
    assert str(info.value).strip() != ""


def test_parse_is_not_called_when_the_request_fails(setup):
    _, parsed = setup(error=ConnectionError("no network"))
    with pytest.raises(WeatherFetchError):
        fetch_weather(LAT, LON)
    assert parsed == []


def test_empty_response_list_becomes_weather_fetch_error(setup):
    setup(responses=[])
    with pytest.raises(WeatherFetchError):
        fetch_weather(LAT, LON)


def test_a_response_that_cannot_be_parsed_becomes_weather_fetch_error(setup):
    error = KeyError("missing")
    setup(parse_error=error)
    with pytest.raises(WeatherFetchError) as info:
        fetch_weather(LAT, LON)
    assert info.value.__cause__ is error
