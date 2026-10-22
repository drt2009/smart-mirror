from datetime import datetime, date, time
from zoneinfo import ZoneInfo

import requests

from f1.models import UpcomingRace


def fetch_next_race():
    version = "1.0.0"
    res = requests.get(
        "https://api.jolpi.ca/ergast/f1/current/next/",
        headers={"User-Agent": f"drt2009-smart-mirror/{version}"},
    )
    res.raise_for_status()

    return _parse_upcoming_race(res.json())


def _parse_upcoming_race(data):
    current_race_data = data["MRData"]["RaceTable"]["Races"][0]
    circuit = current_race_data["Circuit"]
    return UpcomingRace(
        circuit_name=circuit["circuitName"],
        country=circuit['Location']["country"],
        race_date=_build_race_time(current_race_data),
        sprint_race=False
    )

def _build_race_time(data):
    date_object = date.strptime(data['date'], "%Y-%m-%d")
    time_str = data['time']
    clean_string = time_str.replace('Z', '+00:00')
    time_object = time.fromisoformat(clean_string)

    return datetime.combine(date_object, time_object)
