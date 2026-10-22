from datetime import tzinfo, datetime, timedelta
from zoneinfo import ZoneInfo

from f1 import models


def upcoming_race_view(upcoming : models.UpcomingRace):
    return [
        upcoming.circuit_name,
        upcoming.country,
        format_date(upcoming.race_date, datetime.today(), ZoneInfo("America/New_York"))
    ]


def format_date(moment: datetime, today: datetime,
    tz: tzinfo) -> str:
    return format_day(moment, today, tz) + " " + format_time(moment,
                                                             tz) + " "


def format_day(moment: datetime, today: datetime, tz: tzinfo) -> str:
    if today.astimezone(tz).date() >= moment.astimezone(tz).date():
        return "Today"
    elif today.astimezone(tz).date() + timedelta(days=1) == moment.astimezone(
        tz).date():
        return "Tomorrow"
    elif today.astimezone(tz).date() + timedelta(days=7) <= moment.astimezone(
        tz).date():
        return moment.astimezone(tz).strftime("%b") + " " + moment.strftime(
            "%d").lstrip("0")
    else:
        day = moment.astimezone(tz).strftime("%a")

    return day


def format_time(moment: datetime, tz: tzinfo) -> str:
    return moment.astimezone(tz).strftime("%I:%M %p").lstrip("0")