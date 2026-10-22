from datetime import datetime, timedelta, date, time, tzinfo
from zoneinfo import ZoneInfo

from agenda.models import Event


def upcoming(cal, now:datetime, tz: tzinfo = ZoneInfo("America/New_York"), limit=5, days=30):
    if limit < 1 or days < 1:
        raise ValueError("limit or days must be positive")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    start = now.astimezone(tz)
    end = start + timedelta(days=days)

    agenda_events = []

    for event in cal.timeline.overlapping(start, end):
        agenda_events.append(_parse_ical_event(event,tz))
        if len(agenda_events) == limit:
            break

    agenda_events.sort(key=lambda event: (event.start, not event.all_day, event.title))
    return agenda_events

def _parse_ical_event(event,tz:tzinfo):
    return Event(
        title=_sanitize_title(event.summary),
        start=_sanitize_date(event.start,tz),
        end=_sanitize_date(event.end,tz),
        all_day=_is_all_day_event(event),
    )

def _sanitize_title(title: str) -> str:
    if title is None or title.strip() == '':
        return '(No title)'
    else :
        return title.strip()

def _sanitize_date(event_date: datetime|date, tz:tzinfo) -> datetime:
    if isinstance(event_date,datetime):
        return event_date.astimezone(tz)
    return datetime.combine(event_date, time.min, tzinfo=tz)

def _is_all_day_event(event: Event) -> bool:
    return ((isinstance(event.start,date) and not isinstance(event.start,datetime))
            and (isinstance(event.end,date) and not isinstance(event.end,datetime)))