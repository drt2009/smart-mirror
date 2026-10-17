from enum import IntEnum

CURRENT = ("temperature_2m", "apparent_temperature", "weather_code")
DAILY = ("weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_probability_mean")
HOURLY = ("temperature_2m", "apparent_temperature", "weather_code", "precipitation_probability")

CurrentIdx = IntEnum("CurrentIdx", [name.upper() for name in CURRENT], start=0)
DailyIdx = IntEnum("DailyIdx", [name.upper() for name in DAILY], start=0)
HourlyIdx = IntEnum("HourlyIdx", [name.upper() for name in HOURLY], start=0)