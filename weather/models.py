from dataclasses import dataclass
from datetime import date, datetime

@dataclass(frozen=True)
class CurrentWeather:
    temperature: float
    feels_like: float
    weather_code: int
    condition:str

@dataclass(frozen=True)
class HourlyEntry:
    time: datetime
    temperature: float
    feels_like: float
    precipitation_probability: float
    weather_code: int
    condition:str

@dataclass(frozen=True)
class DailyEntry:
    date: date
    high: float
    low: float
    precipitation_probability: float
    weather_code: int
    condition: str

@dataclass(frozen=True)
class WeatherSnapshot:
    current: CurrentWeather
    hourly: tuple[HourlyEntry, ...]
    daily: tuple[DailyEntry, ...]
