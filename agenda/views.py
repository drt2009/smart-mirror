from datetime import datetime, tzinfo, timedelta, timezone
from zoneinfo import ZoneInfo

from agenda.models import Event


def agenda_lines(events:list[Event], now:datetime, tz: tzinfo = ZoneInfo("America/New_York")) -> list[str]:
    if len(events) == 0:
        return ['Nothing coming up']

    if now.tzinfo is None:
        raise ValueError("now must be have tzinfo")

    lines = []
    for event in events:
        line_parts = [
            format_date(event.start, now, event.all_day,tz),
            event.title,
        ]
        lines.append(" ".join(part for part in line_parts if part))
    return lines

def format_date(moment: datetime,  today:datetime, all_day: bool, tz: tzinfo) -> str:
    return format_day(moment, today, tz)+" " +format_time(moment, all_day,tz)+" "

def format_day(moment: datetime, today:datetime, tz: tzinfo) -> str:
    if today.astimezone(tz).date() >= moment.astimezone(tz).date() :
        return "Today"
    elif today.astimezone(tz).date() + timedelta(days=1) == moment.astimezone(tz).date():
        return "Tomorrow"
    elif today.astimezone(tz).date() + timedelta(days=7) <=moment.astimezone(tz).date():
        return moment.astimezone(tz).strftime("%b")+" "+moment.strftime( "%d").lstrip("0")
    else:
       day = moment.astimezone(tz).strftime("%a")

    return day

def format_time(moment: datetime, all_day: bool, tz: tzinfo) -> str:
    if all_day:
        return "All day"
    else:
        return moment.astimezone(tz).strftime("%I:%M %p").lstrip("0")