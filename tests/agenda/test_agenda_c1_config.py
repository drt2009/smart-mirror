"""C1, AC 1: config.load_calendar_url() (project root, next to main.py).

Contract
--------
config.py defines

    load_calendar_url() -> str

* Calls ``load_dotenv()`` each time it runs (not at import time), the same way
  ``load_location()`` does.
* Returns the value of CALENDAR_URL with surrounding whitespace removed.
* Raises ValueError, naming CALENDAR_URL, when it is missing, empty, or only
  whitespace.

The tests never touch your real .env: load_dotenv is replaced with a stub and
the variable is cleared before every test.
"""
import pytest

import config

URL = "https://calendar.google.com/calendar/ical/me%40example.com/private-abc123/basic.ics"


@pytest.fixture(autouse=True)
def dotenv_calls(monkeypatch):
    calls = []

    def fake_load_dotenv(*args, **kwargs):
        calls.append((args, kwargs))
        return False

    monkeypatch.setattr(config, "load_dotenv", fake_load_dotenv)
    monkeypatch.delenv("SECRET_ICAL_URL", raising=False)
    return calls


def test_returns_the_url(monkeypatch):
    monkeypatch.setenv("SECRET_ICAL_URL", URL)
    assert config.load_calendar_url() == URL


def test_the_url_is_a_str(monkeypatch):
    monkeypatch.setenv("SECRET_ICAL_URL", URL)
    assert type(config.load_calendar_url()) is str


def test_surrounding_whitespace_is_removed(monkeypatch):
    monkeypatch.setenv("SECRET_ICAL_URL", f"  {URL}\n")
    assert config.load_calendar_url() == URL


def test_loads_dotenv_when_called(monkeypatch, dotenv_calls):
    monkeypatch.setenv("SECRET_ICAL_URL", URL)
    assert dotenv_calls == []  # nothing happens at import time
    config.load_calendar_url()
    assert len(dotenv_calls) >= 1


def test_missing_url_names_the_variable():
    with pytest.raises(ValueError, match="SECRET_ICAL_URL"):
        config.load_calendar_url()


@pytest.mark.parametrize("blank", ["", " ", "   ", "\t"], ids=["empty", "space", "spaces", "tab"])
def test_empty_or_blank_url_is_treated_as_missing(monkeypatch, blank):
    monkeypatch.setenv("SECRET_ICAL_URL", blank)
    with pytest.raises(ValueError, match="SECRET_ICAL_URL"):
        config.load_calendar_url()

