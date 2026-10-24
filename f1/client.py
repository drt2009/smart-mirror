from datetime import datetime, date, time
import requests

from f1.models import UpcomingRace

DEFAULT_TIMEOUT = 30.0

class F1FetchError(Exception):
    pass

def fetch_next_race(timeout = DEFAULT_TIMEOUT):
    if timeout < 0:
        raise AttributeError("Timeout must be non-negative")
    try:
        version = "1.0.0"
        res = requests.get(
            "https://api.jolpi.ca/ergast/f1/current/next/",
            timeout=timeout,
            headers={"User-Agent": f"drt2009-smart-mirror/{version}"},
        )
        res.raise_for_status()
        return parse_upcoming_race(res.json())
    except Exception as e:
        raise F1FetchError from e




def parse_upcoming_race(data):
    if len(data["MRData"]["RaceTable"]["Races"]) == 0:
        return None
    current_race_data = data["MRData"]["RaceTable"]["Races"][0]
    circuit = current_race_data["Circuit"]
    return UpcomingRace(
        circuit_name=circuit["circuitName"],
        country=circuit['Location']["country"],
        race_date=_build_race_time(current_race_data),
        sprint_race=_is_sprint(current_race_data),
        race_name = current_race_data["raceName"],
    )

def _build_race_time(data):
    date_object = date.fromisoformat(data['date'])
    time_str = data['time']
    clean_string = time_str.replace('Z', '+00:00')
    time_object = time.fromisoformat(clean_string)

    return datetime.combine(date_object, time_object)

def _is_sprint(data):
    return bool(data.get("Sprint", False))
