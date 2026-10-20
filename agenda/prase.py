from datetime import datetime, timedelta, date, time
from agenda.models import Event


def parse(cal, number_to_parse):
    start = datetime.now()
    end = start + timedelta(days=30)

    agenda_events = []

    for event in cal.timeline.overlapping(start, end):
        agenda_events.append(_parse_ical_event(event))
        if len(agenda_events) == number_to_parse:
            break
    return agenda_events

def _parse_ical_event(event):
    return Event(
        title=event.summary,
        start=event.start,
        end=event.end,
    )