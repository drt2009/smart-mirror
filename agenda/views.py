from datetime import datetime, tzinfo, timedelta, timezone
from zoneinfo import ZoneInfo

from agenda.models import Event

def agenda_rows(events:list[Event], now:datetime, tz: tzinfo = ZoneInfo("America/New_York")):
    if now.tzinfo is None:
        raise ValueError("now must be have tzinfo")

    if len(events) == 0:
        return [['Nothing coming up','','']]

    lines = []
    for event in events:
        line_parts = [
            format_day(event.start,now,tz),
            format_time(event.start,event.all_day,tz),
            event.title,
        ]
        lines.append(line_parts)
    return lines

def format_date(moment: datetime,  today:datetime, all_day: bool, tz: tzinfo) -> str:
    return format_day(moment, today, tz)+" " +format_time(moment, all_day,tz)+" "

def format_day(moment: datetime, today:datetime, tz: tzinfo) -> str:
    today_date = today.astimezone(tz).date()
    event_in_timezone = moment.astimezone(tz)
    if today_date >= event_in_timezone.date() :
        return "Today"
    elif today_date + timedelta(days=1) == event_in_timezone.date():
        return "Tomorrow"
    elif today_date + timedelta(days=7) <=event_in_timezone.date():
        return event_in_timezone.strftime("%b")+" "+event_in_timezone.strftime( "%d").lstrip("0")
    else:
       day = event_in_timezone.strftime("%a")

    return day

def format_time(moment: datetime, all_day: bool, tz: tzinfo) -> str:
    if all_day:
        return "All day"
    else:
        return moment.astimezone(tz).strftime("%I:%M %p").lstrip("0")