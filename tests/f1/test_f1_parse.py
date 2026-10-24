"""F1 parsing: f1/client.py -> parse_upcoming_race(data) and f1/models.py -> UpcomingRace.

Contract
--------
UpcomingRace (frozen dataclass, f1/models.py), fields:
    race_name     "Miami Grand Prix"   <- the API's raceName
    circuit_name  "Miami International Autodrome"
    country       "USA"
    race_date     a timezone-AWARE datetime, the race start
    sprint_race   bool

parse_upcoming_race(data: dict) -> UpcomingRace | None
    data is the decoded JSON of https://api.jolpi.ca/ergast/f1/current/next/
    * The first entry of MRData.RaceTable.Races is the race.
    * An EMPTY Races list means the season is over: the result is None.
    * race_date is built from the API's "date" + "time" ("2026-11-08", "20:00:00Z")
      and is UTC. It must not depend on the machine's time zone or Python version.
    * sprint_race is True exactly when the race entry has a "Sprint" key.
    * Broken data (no MRData, no time, ...) raises: it never returns a half-filled race.
    * The input dict is not changed.
"""
import copy
import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from f1.client import parse_upcoming_race
from f1.models import UpcomingRace

UTC = timezone.utc


def race_entry(**overrides):
    entry = {
        "season": "2026",
        "round": "21",
        "raceName": "Miami Grand Prix",
        "Circuit": {
            "circuitId": "miami",
            "circuitName": "Miami International Autodrome",
            "Location": {"lat": "25.9581", "long": "-80.2389",
                         "locality": "Miami", "country": "USA"},
        },
        "date": "2026-11-08",
        "time": "20:00:00Z",
    }
    entry.update(overrides)
    return entry


def payload(*races):
    return {"MRData": {"RaceTable": {"season": "2026", "Races": list(races)}}}


class TestTheRace:
    def test_the_grand_prix_name_comes_from_race_name(self):
        assert parse_upcoming_race(payload(race_entry())).race_name == "Miami Grand Prix"

    def test_the_circuit_name_is_read(self):
        race = parse_upcoming_race(payload(race_entry()))
        assert race.circuit_name == "Miami International Autodrome"

    def test_the_country_is_read_from_the_circuit_location(self):
        assert parse_upcoming_race(payload(race_entry())).country == "USA"

    def test_circuit_name_and_race_name_are_not_mixed_up(self):
        entry = race_entry(raceName="Race A")
        entry["Circuit"]["circuitName"] = "Circuit B"
        race = parse_upcoming_race(payload(entry))
        assert (race.race_name, race.circuit_name) == ("Race A", "Circuit B")

    def test_the_first_race_in_the_list_is_the_one_used(self):
        later = race_entry(raceName="Later Grand Prix", date="2026-12-01")
        race = parse_upcoming_race(payload(race_entry(), later))
        assert race.race_name == "Miami Grand Prix"

    def test_a_result_is_an_upcoming_race(self):
        assert isinstance(parse_upcoming_race(payload(race_entry())), UpcomingRace)


class TestTheStartTime:
    def test_date_and_time_become_a_utc_datetime(self):
        race = parse_upcoming_race(payload(race_entry()))
        assert race.race_date == datetime(2026, 11, 8, 20, 0, tzinfo=UTC)

    def test_the_datetime_is_timezone_aware_with_a_zero_offset(self):
        race = parse_upcoming_race(payload(race_entry()))
        assert race.race_date.utcoffset() == timedelta(0)

    def test_the_time_is_not_relabelled_as_another_zone(self):
        race = parse_upcoming_race(payload(race_entry(time="07:30:00Z")))
        assert race.race_date.astimezone(UTC).hour == 7
        assert race.race_date.astimezone(UTC).minute == 30

    def test_a_race_just_after_midnight_utc_keeps_its_utc_date(self):
        race = parse_upcoming_race(payload(race_entry(date="2026-03-02", time="00:30:00Z")))
        assert race.race_date == datetime(2026, 3, 2, 0, 30, tzinfo=UTC)

    def test_the_result_does_not_depend_on_the_machine_time_zone(self, monkeypatch):
        import time
        if not hasattr(time, "tzset"):
            pytest.skip("time.tzset is not available on this platform")
        results = []
        for name in ("UTC", "Asia/Tokyo", "America/Los_Angeles"):
            monkeypatch.setenv("TZ", name)
            time.tzset()
            results.append(parse_upcoming_race(payload(race_entry())).race_date)
        monkeypatch.undo()
        time.tzset()
        assert results[0] == results[1] == results[2]


class TestSprintWeekends:
    def test_a_race_without_a_sprint_key_is_not_a_sprint_race(self):
        assert parse_upcoming_race(payload(race_entry())).sprint_race is False

    def test_a_race_with_a_sprint_key_is_a_sprint_race(self):
        entry = race_entry(Sprint={"date": "2026-11-07", "time": "16:00:00Z"})
        assert parse_upcoming_race(payload(entry)).sprint_race is True

    def test_sprint_race_is_a_real_bool(self):
        entry = race_entry(Sprint={"date": "2026-11-07", "time": "16:00:00Z"})
        assert type(parse_upcoming_race(payload(entry)).sprint_race) is bool


class TestTheSeasonIsOver:
    def test_an_empty_race_list_gives_none(self):
        assert parse_upcoming_race(payload()) is None


class TestBrokenData:
    @pytest.mark.parametrize("data", [
        {},
        {"MRData": {}},
        {"MRData": {"RaceTable": {}}},
        None,
        [],
    ])
    def test_a_missing_structure_raises(self, data):
        with pytest.raises(Exception):
            parse_upcoming_race(data)

    @pytest.mark.parametrize("missing", ["raceName", "Circuit", "date", "time"])
    def test_a_race_missing_a_field_raises_instead_of_returning_a_partial_race(self, missing):
        entry = race_entry()
        del entry[missing]
        with pytest.raises(Exception):
            parse_upcoming_race(payload(entry))

    def test_a_circuit_without_a_country_raises(self):
        entry = race_entry()
        del entry["Circuit"]["Location"]["country"]
        with pytest.raises(Exception):
            parse_upcoming_race(payload(entry))

    def test_an_unreadable_date_raises(self):
        with pytest.raises(Exception):
            parse_upcoming_race(payload(race_entry(date="next sunday")))

    def test_an_unreadable_time_raises(self):
        with pytest.raises(Exception):
            parse_upcoming_race(payload(race_entry(time="afternoon")))


def test_parsing_does_not_change_its_input():
    data = payload(race_entry(Sprint={"date": "2026-11-07", "time": "16:00:00Z"}))
    before = copy.deepcopy(data)
    parse_upcoming_race(data)
    assert data == before


class TestTheModel:
    def make(self):
        return UpcomingRace(
            race_name="Miami Grand Prix",
            circuit_name="Miami International Autodrome",
            country="USA",
            race_date=datetime(2026, 11, 8, 20, 0, tzinfo=UTC),
            sprint_race=False,
        )

    def test_it_is_a_dataclass(self):
        assert dataclasses.is_dataclass(UpcomingRace)

    def test_it_is_frozen(self):
        race = self.make()
        with pytest.raises(dataclasses.FrozenInstanceError):
            race.race_name = "Other"

    def test_it_has_exactly_these_fields(self):
        names = {f.name for f in dataclasses.fields(UpcomingRace)}
        assert names == {"race_name", "circuit_name", "country", "race_date", "sprint_race"}

    def test_equal_races_compare_equal_and_hash_alike(self):
        assert self.make() == self.make()
        assert hash(self.make()) == hash(self.make())

    @pytest.mark.parametrize("left_out", [
        "race_name", "circuit_name", "country", "race_date", "sprint_race"])
    def test_every_field_has_to_be_given(self, left_out):
        values = dict(
            race_name="Miami Grand Prix",
            circuit_name="Miami International Autodrome",
            country="USA",
            race_date=datetime(2026, 11, 8, 20, 0, tzinfo=UTC),
            sprint_race=False,
        )
        del values[left_out]
        with pytest.raises(TypeError):
            UpcomingRace(**values)
