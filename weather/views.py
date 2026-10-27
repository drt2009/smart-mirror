from datetime import datetime, date

import weather.models as models

def current_view(snapshot : models.WeatherSnapshot) -> list[str]:
    current = snapshot.current
    return [
        format_temperature(current.temperature),
        current.condition,
        f"Feels like {format_temperature(current.feels_like)}",
    ]

def hourly_rows(snapshot : models.WeatherSnapshot):
    lines = []
    for hour in snapshot.hourly:
        line_parts = [
            format_hour(hour.time),
            format_temperature(hour.temperature),
            hour.condition,
            format_chance(hour.precipitation_probability)
        ]
        lines.append(line_parts)
    return lines

def daily_rows(snapshot : models.WeatherSnapshot, today: date):
    lines = []
    for day in snapshot.daily:
        line_parts = [
            format_day(day.date, today),
            format_temperature(day.high),
            format_temperature(day.low),
            day.condition,
            format_chance(day.precipitation_probability)
        ]
        lines.append(line_parts)
    return lines

#helpers
def format_chance(percent: float) -> str:
    if percent < 20:
        return ""
    else:
        return f"{round(percent)}%"

def format_day(day: date, today:date) -> str:
    if day == today :
        return "Today"
    else:
        return day.strftime("%a")

def format_hour(moment: datetime) -> str:
    return moment.strftime("%I %p").lstrip("0")

def format_temperature(value: float) -> str:
    return  f"{round(value)}°"