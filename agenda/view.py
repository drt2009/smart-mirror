from datetime import datetime

def agenda_view(events):
    lines = []
    for event in events:
        line_parts = [
            format_date(event.start),
            format_date(event.end),
            event.title,
        ]
        lines.append(" ".join(part for part in line_parts if part))
    return lines

def format_date(moment: datetime) -> str:
    return moment.strftime("%a %I %p").replace(" 0", " ")