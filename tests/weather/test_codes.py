"""Tests for weather/codes.py.

Contract
--------
get_description(code) -> str

* ``code`` is a WMO weather code as Open-Meteo sends it: usually a float
  (3.0), sometimes a numpy float32, occasionally NaN or None.
* Every documented code returns a non-empty, human-readable description.
* Anything unrecognised returns ONE shared fallback string and never raises.

The tests deliberately don't pin exact wording, so you can keep whatever text
you already have.
"""
import numpy as np
import pytest

from weather.codes import get_description

# Every code Open-Meteo documents.
WMO_CODES = [
    0, 1, 2, 3,
    45, 48,
    51, 53, 55, 56, 57,
    61, 63, 65, 66, 67,
    71, 73, 75, 77,
    80, 81, 82,
    85, 86,
    95, 96, 97, 99,
]

UNKNOWN_CODES = [-1, 4, 10, 44, 100, 999]


@pytest.fixture
def fallback():
    """Whatever the module returns for a code it doesn't know."""
    return get_description(-1)


def test_fallback_is_a_nonempty_string(fallback):
    assert isinstance(fallback, str)
    assert fallback.strip() != ""


@pytest.mark.parametrize("code", WMO_CODES)
def test_known_code_returns_clean_nonempty_string(code):
    text = get_description(code)
    assert isinstance(text, str)
    assert text != ""
    assert text == text.strip()


@pytest.mark.parametrize("code", WMO_CODES)
def test_known_code_is_not_the_fallback(code, fallback):
    assert get_description(code) != fallback


@pytest.mark.parametrize("code", UNKNOWN_CODES)
def test_unknown_code_returns_the_fallback(code, fallback):
    assert get_description(code) == fallback


@pytest.mark.parametrize("value", [float("nan"), None])
def test_invalid_values_return_the_fallback_instead_of_raising(value, fallback):
    assert get_description(value) == fallback


@pytest.mark.parametrize("code", WMO_CODES)
def test_float_and_int_give_the_same_answer(code):
    assert get_description(float(code)) == get_description(code)


@pytest.mark.parametrize("code", [0, 3, 61, 95])
def test_numpy_floats_are_accepted(code):
    # ValuesAsNumpy() hands you numpy float32 values.
    assert get_description(np.float32(code)) == get_description(code)


def test_broad_categories_are_distinguishable():
    representatives = {
        "clear": 0,
        "overcast": 3,
        "fog": 45,
        "rain": 63,
        "snow": 73,
        "thunderstorm": 95,
    }
    texts = [get_description(code) for code in representatives.values()]
    assert len(set(texts)) == len(texts)