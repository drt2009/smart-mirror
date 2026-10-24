from datetime import tzinfo, datetime, timedelta

from f1 import models
from f1.state import F1State


def upcoming_race_view(race : models.UpcomingRace, now, tz):
    race_data = [
        race.race_name,
        race.circuit_name + ', ' + race.country,
        format_when(race.race_date, now, tz)
    ]
    if race.sprint_race:
        race_data.append("Sprint weekend")
    return race_data

def format_when(moment: datetime, today: datetime,
    tz: tzinfo) -> str:
    return format_day(moment, today, tz) + " " + format_time(moment,tz)

def f1_lines(state:F1State, now, tz) -> list[str]:
    if state.is_loading and not state.last_fetch_failed:
        return ["Loading..."]
    elif not state.race and state.last_fetch_failed:
        return ["Fetch Failed"]
    elif not state.race and not state.last_fetch_failed:
        return ["Season Over"]
    else:
        return upcoming_race_view(state.race, now, tz)


def format_day(moment: datetime, today: datetime, tz: tzinfo) -> str:
    moment = moment.astimezone(tz)
    if today.astimezone(tz).date() >= moment.date():
        return "Today"
    elif today.astimezone(tz).date() + timedelta(days=1) == moment.date():
        return "Tomorrow"
    elif today.astimezone(tz).date() + timedelta(days=7) <= moment.date():
        return moment.strftime("%b") + " " + moment.strftime(
            "%d").lstrip("0")
    else:
        return moment.strftime("%a")

def format_time(moment: datetime, tz: tzinfo) -> str:
    return moment.astimezone(tz).strftime("%I:%M %p").lstrip("0")

