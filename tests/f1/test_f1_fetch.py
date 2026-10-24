"""F1 fetching: f1/client.py -> fetch_next_race().

Contract
--------
f1/client.py defines

    class F1FetchError(Exception)
    def fetch_next_race()          # -> UpcomingRace | None

* One GET to https://api.jolpi.ca/ergast/f1/current/next/ through the module's
  ``requests.get`` (looked up when the function runs, so tests can swap it).
* The call sends a User-Agent header that names the app (contains "smart-mirror")
  and a positive ``timeout``: a hung connection must not block the worker thread
  forever.
* ``raise_for_status()`` is called, so a 4xx/5xx is a failure, not a parse attempt.
* The decoded JSON goes through parse_upcoming_race (looked up when the function
  runs) and its result, including None, is returned as it is.
* ANY failure (network error, bad status, invalid JSON, unparseable data) is raised
  as F1FetchError with the original exception chained as __cause__.
* Nothing is fetched at import time. No test here touches the network.
"""
from datetime import datetime, timezone

import pytest
import requests

import f1.client as client
from f1.client import F1FetchError, fetch_next_race

URL = "https://api.jolpi.ca/ergast/f1/current/next/"
UTC = timezone.utc

DATA = {"MRData": {"RaceTable": {"Races": [{
    "raceName": "Miami Grand Prix",
    "Circuit": {"circuitName": "Miami International Autodrome",
                "Location": {"country": "USA"}},
    "date": "2026-11-08",
    "time": "20:00:00Z",
}]}}}


class FakeResponse:
    def __init__(self, data=None, status_error=None, json_error=None):
        self.data = DATA if data is None else data
        self.status_error = status_error
        self.json_error = json_error
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True
        if self.status_error is not None:
            raise self.status_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.data


@pytest.fixture
def http(monkeypatch):
    calls = []

    def install(response=None, error=None):
        response = response or FakeResponse()

        def fake_get(url, *args, **kwargs):
            calls.append((url, args, kwargs))
            if error is not None:
                raise error
            return response

        monkeypatch.setattr(client.requests, "get", fake_get)
        return response

    install.calls = calls
    return install


class TestTheRequest:
    def test_one_request_goes_to_the_next_race_endpoint(self, http):
        http()
        fetch_next_race()
        assert len(http.calls) == 1
        assert http.calls[0][0] == URL

    def test_a_user_agent_naming_the_app_is_sent(self, http):
        http()
        fetch_next_race()
        headers = http.calls[0][2]["headers"]
        assert "smart-mirror" in headers["User-Agent"]

    def test_a_positive_timeout_is_set(self, http):
        http()
        fetch_next_race()
        timeout = http.calls[0][2]["timeout"]
        values = timeout if isinstance(timeout, tuple) else (timeout,)
        assert values and all(isinstance(v, (int, float)) and v > 0 for v in values)

    def test_the_status_is_checked(self, http):
        response = http()
        fetch_next_race()
        assert response.status_checked

    def test_nothing_is_fetched_just_by_importing(self, monkeypatch):
        import importlib.util
        calls = []
        monkeypatch.setattr(requests, "get", lambda *a, **k: calls.append(a))
        spec = importlib.util.spec_from_file_location("f1_client_fresh_copy", client.__file__)
        importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importlib.util.module_from_spec(spec))
        assert calls == []


class TestTheResult:
    def test_the_response_becomes_an_upcoming_race(self, http):
        http()
        race = fetch_next_race()
        assert race.race_name == "Miami Grand Prix"
        assert race.country == "USA"
        assert race.race_date == datetime(2026, 11, 8, 20, 0, tzinfo=UTC)

    def test_the_decoded_json_is_what_gets_parsed(self, http, monkeypatch):
        http()
        seen = []
        sentinel = object()
        monkeypatch.setattr(client, "parse_upcoming_race",
                            lambda data: seen.append(data) or sentinel)
        assert fetch_next_race() is sentinel
        assert seen == [DATA]

    def test_a_finished_season_gives_none(self, http):
        http(FakeResponse({"MRData": {"RaceTable": {"Races": []}}}))
        assert fetch_next_race() is None


class TestFailures:
    @pytest.mark.parametrize("error", [
        requests.ConnectionError("down"),
        requests.Timeout("slow"),
        OSError("socket"),
    ])
    def test_a_network_error_is_an_f1_fetch_error(self, http, error):
        http(error=error)
        with pytest.raises(F1FetchError) as raised:
            fetch_next_race()
        assert raised.value.__cause__ is error

    def test_a_bad_status_is_an_f1_fetch_error(self, http):
        error = requests.HTTPError("503")
        http(FakeResponse(status_error=error))
        with pytest.raises(F1FetchError) as raised:
            fetch_next_race()
        assert raised.value.__cause__ is error

    def test_invalid_json_is_an_f1_fetch_error(self, http):
        error = ValueError("not json")
        http(FakeResponse(json_error=error))
        with pytest.raises(F1FetchError) as raised:
            fetch_next_race()
        assert raised.value.__cause__ is error

    def test_unparseable_data_is_an_f1_fetch_error(self, http):
        http(FakeResponse({"unexpected": True}))
        with pytest.raises(F1FetchError) as raised:
            fetch_next_race()
        assert raised.value.__cause__ is not None

    def test_the_error_is_an_exception_subclass(self):
        assert issubclass(F1FetchError, Exception)
