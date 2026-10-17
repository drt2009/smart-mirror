"""Tests for config.py (project root, next to main.py).

Contract
--------
config.py does ``from dotenv import load_dotenv`` at module level and defines

    load_location() -> tuple[float, float]      # (latitude, longitude)

* Calls ``load_dotenv()`` each time it runs (not at import time).
* Reads LATITUDE and LONGITUDE from the environment, returns them as floats.
* Raises ValueError, naming the variable, when a value is missing, empty,
  not a number, NaN/infinite, or out of range.
    latitude  -90 .. 90   (inclusive)
    longitude -180 .. 180 (inclusive)

The tests never touch your real .env: load_dotenv is replaced with a stub and
both variables are cleared before every test.
"""
import pytest

import config


@pytest.fixture(autouse=True)
def dotenv_calls(monkeypatch):
    """Replace load_dotenv with a stub and clear both variables."""
    calls = []

    def fake_load_dotenv(*args, **kwargs):
        calls.append((args, kwargs))
        return False

    monkeypatch.setattr(config, "load_dotenv", fake_load_dotenv)
    monkeypatch.delenv("LATITUDE", raising=False)
    monkeypatch.delenv("LONGITUDE", raising=False)
    return calls


@pytest.fixture
def env(monkeypatch):
    def _set(lat=None, lon=None):
        if lat is not None:
            monkeypatch.setenv("LATITUDE", lat)
        if lon is not None:
            monkeypatch.setenv("LONGITUDE", lon)

    return _set


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------
def test_returns_latitude_and_longitude(env):
    env("42.475136", "-83.221275")
    assert config.load_location() == (42.475136, -83.221275)


def test_values_are_plain_floats(env):
    env("42.5", "-83.2")
    lat, lon = config.load_location()
    assert type(lat) is float
    assert type(lon) is float


def test_whole_numbers_are_accepted_and_become_floats(env):
    env("40", "-74")
    lat, lon = config.load_location()
    assert (lat, lon) == (40.0, -74.0)
    assert type(lat) is float


@pytest.mark.parametrize(
    "lat, lon",
    [("90", "180"), ("-90", "-180"), ("0", "0")],
    ids=["max", "min", "zero"],
)
def test_range_limits_are_inclusive(env, lat, lon):
    env(lat, lon)
    assert config.load_location() == (float(lat), float(lon))


def test_loads_dotenv_when_called(env, dotenv_calls):
    env("42.5", "-83.2")
    assert dotenv_calls == []  # nothing happens at import time
    config.load_location()
    assert len(dotenv_calls) >= 1


# --------------------------------------------------------------------------
# Missing / empty
# --------------------------------------------------------------------------
def test_missing_latitude_names_the_variable(env):
    env(lon="-83.2")
    with pytest.raises(ValueError, match="LATITUDE"):
        config.load_location()


def test_missing_longitude_names_the_variable(env):
    env(lat="42.5")
    with pytest.raises(ValueError, match="LONGITUDE"):
        config.load_location()


def test_both_missing_fails(env):
    with pytest.raises(ValueError):
        config.load_location()


@pytest.mark.parametrize("name", ["LATITUDE", "LONGITUDE"])
def test_empty_value_is_treated_as_missing(monkeypatch, env, name):
    env("42.5", "-83.2")
    monkeypatch.setenv(name, "")
    with pytest.raises(ValueError, match=name):
        config.load_location()


# --------------------------------------------------------------------------
# Not a number
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["LATITUDE", "LONGITUDE"])
def test_non_numeric_value_names_the_variable_and_the_value(monkeypatch, env, name):
    env("42.5", "-83.2")
    monkeypatch.setenv(name, "abc")
    with pytest.raises(ValueError, match=name) as info:
        config.load_location()
    assert "abc" in str(info.value)


def test_non_numeric_error_hides_the_inner_conversion_error(env):
    env("not-a-number", "-83.2")
    with pytest.raises(ValueError) as info:
        config.load_location()
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__ is True


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
@pytest.mark.parametrize("name", ["LATITUDE", "LONGITUDE"])
def test_nan_and_infinity_are_rejected(monkeypatch, env, name, bad):
    env("42.5", "-83.2")
    monkeypatch.setenv(name, bad)
    with pytest.raises(ValueError, match=name):
        config.load_location()


# --------------------------------------------------------------------------
# Out of range
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["90.1", "-90.1", "91", "-200", "1000"])
def test_latitude_out_of_range(env, bad):
    env(bad, "-83.2")
    with pytest.raises(ValueError, match="LATITUDE"):
        config.load_location()


@pytest.mark.parametrize("bad", ["180.1", "-180.1", "181", "-360", "1000"])
def test_longitude_out_of_range(env, bad):
    env("42.5", bad)
    with pytest.raises(ValueError, match="LONGITUDE"):
        config.load_location()


def test_swapped_values_are_caught_by_the_range_check(env):
    # Easy mistake: longitude in the latitude slot.
    env("-120.0", "42.5")
    with pytest.raises(ValueError, match="LATITUDE"):
        config.load_location()
