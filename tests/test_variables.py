"""Tests for weather/variables.py.

Contract
--------
For each of the three Open-Meteo groups, variables.py defines:

* an ordered sequence of variable-name strings: CURRENT, HOURLY, DAILY
* an IntEnum of the same names, UPPERCASED, whose value is each name's
  position in that sequence: CurrentIdx, HourlyIdx, DailyIdx

The sequences are what you send to the API. The enums are how you read the
response. Because both come from the same list, they can never drift apart.
"""
import re
from enum import IntEnum

import pytest

from weather.variables import (
    CURRENT,
    DAILY,
    HOURLY,
    CurrentIdx,
    DailyIdx,
    HourlyIdx,
)

GROUPS = [
    pytest.param(CURRENT, CurrentIdx, id="current"),
    pytest.param(HOURLY, HourlyIdx, id="hourly"),
    pytest.param(DAILY, DailyIdx, id="daily"),
]

# Variables the UI needs. Extend this as you add features.
REQUIRED = [
    pytest.param(
        CURRENT,
        {"temperature_2m", "apparent_temperature", "weather_code"},
        id="current",
    ),
    pytest.param(
        HOURLY,
        {
            "temperature_2m",
            "apparent_temperature",
            "weather_code",
            "precipitation_probability",
        },
        id="hourly",
    ),
    pytest.param(
        DAILY,
        {
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        },
        id="daily",
    ),
]


@pytest.mark.parametrize("names, idx", GROUPS)
def test_names_are_a_nonempty_sequence_of_strings(names, idx):
    assert isinstance(names, (list, tuple))
    assert len(names) > 0
    assert all(isinstance(n, str) for n in names)


@pytest.mark.parametrize("names, idx", GROUPS)
def test_names_have_no_duplicates(names, idx):
    assert len(set(names)) == len(names)


@pytest.mark.parametrize("names, idx", GROUPS)
def test_names_are_lowercase_snake_case(names, idx):
    for name in names:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), name


@pytest.mark.parametrize("names, idx", GROUPS)
def test_index_enum_is_an_intenum(names, idx):
    assert issubclass(idx, IntEnum)


@pytest.mark.parametrize("names, idx", GROUPS)
def test_enum_has_exactly_one_member_per_name(names, idx):
    assert len(idx) == len(names)
    assert {member.name for member in idx} == {n.upper() for n in names}


@pytest.mark.parametrize("names, idx", GROUPS)
def test_enum_value_is_the_position_in_the_list(names, idx):
    for position, name in enumerate(names):
        assert idx[name.upper()].value == position, name


@pytest.mark.parametrize("names, idx", GROUPS)
def test_enum_values_are_contiguous_from_zero(names, idx):
    assert sorted(member.value for member in idx) == list(range(len(names)))


@pytest.mark.parametrize("names, idx", GROUPS)
def test_enum_members_work_as_list_indexes(names, idx):
    # IntEnum members can be used directly as an index into a sequence.
    for name in names:
        assert names[idx[name.upper()]] == name


@pytest.mark.parametrize("names, required", REQUIRED)
def test_required_variables_are_requested(names, required):
    missing = required - set(names)
    assert not missing, f"missing from request list: {sorted(missing)}"
