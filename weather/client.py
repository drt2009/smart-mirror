from weather.codes import get_description
from weather.models import CurrentWeather, HourlyEntry, DailyEntry, WeatherSnapshot
import weather.variables as weather_variables
from datetime import datetime, timedelta, timezone
from typing import Final
import openmeteo_requests

HOURLY_COUNT: Final = 4
DAILY_COUNT: Final = 3
_TIMEOUT_SECONDS: Final = 10
_API_URL: Final = "https://api.open-meteo.com/v1/forecast"

class WeatherFetchError(Exception):
    pass

def fetch_weather(lat: float, lon: float) -> WeatherSnapshot:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": list(weather_variables.DAILY),
        "hourly": list(weather_variables.HOURLY),
        "current":list(weather_variables.CURRENT),
        "timezone": "auto",
        "forecast_days": DAILY_COUNT,
        "forecast_hours": HOURLY_COUNT,
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
    }

    try:
        responses = _get_client().weather_api(_API_URL, params=params, timeout=_TIMEOUT_SECONDS)
        return parse(responses[0])
    except Exception as e:
        raise WeatherFetchError(e) from e

def _get_client():
    return openmeteo_requests.Client()

def parse(response) -> WeatherSnapshot:
    tz = timezone(timedelta(seconds=response.UtcOffsetSeconds()))
    return WeatherSnapshot(
        current= _parse_current(response),
        hourly= _parse_hourly(response,tz),
        daily= _parse_daily(response,tz)
    )

def _parse_current(response):
    current = response.Current()
    current_weather_code = int(current.Variables(weather_variables.CurrentIdx.WEATHER_CODE).Value())

    return CurrentWeather(
        temperature=float(current.Variables(weather_variables.CurrentIdx.TEMPERATURE_2M).Value()),
        feels_like=float(current.Variables(weather_variables.CurrentIdx.APPARENT_TEMPERATURE).Value()),
        weather_code=current_weather_code,
        condition=get_description(current_weather_code),
    )

def _parse_hourly(response, tz):
    hourly = response.Hourly()
    temperatures = hourly.Variables(weather_variables.HourlyIdx.TEMPERATURE_2M).ValuesAsNumpy()
    feel_likes = hourly.Variables(weather_variables.HourlyIdx.APPARENT_TEMPERATURE).ValuesAsNumpy()
    weather_codes = hourly.Variables(weather_variables.HourlyIdx.WEATHER_CODE).ValuesAsNumpy()
    precipitation_probabilities = hourly.Variables(weather_variables.HourlyIdx.PRECIPITATION_PROBABILITY).ValuesAsNumpy()
    times =  _local_times(hourly, len(temperatures), tz)

    return tuple(
        HourlyEntry(
            time=t,
            temperature=float(temperature),
            feels_like= float(feel_like),
            precipitation_probability = float(precipitation_probability),
            weather_code=int(weather_code),
            condition=get_description(weather_code),
        )
        for t, temperature, feel_like, weather_code,precipitation_probability in zip(times, temperatures, feel_likes, weather_codes, precipitation_probabilities, strict=True)
    )

def _parse_daily(response,tz):
    daily = response.Daily()
    highs = daily.Variables(weather_variables.DailyIdx.TEMPERATURE_2M_MAX).ValuesAsNumpy()
    lows = daily.Variables(weather_variables.DailyIdx.TEMPERATURE_2M_MIN).ValuesAsNumpy()
    weather_codes = daily.Variables(weather_variables.DailyIdx.WEATHER_CODE).ValuesAsNumpy()
    precipitation_probabilities = daily.Variables(weather_variables.DailyIdx.PRECIPITATION_PROBABILITY_MEAN).ValuesAsNumpy()
    dates = _local_times(daily, len(highs), tz)

    return tuple(
        DailyEntry(
            date = d.date(),
            high = float(high),
            low = float(low),
            precipitation_probability = float(precipitation_probability),
            weather_code=int(weather_code),
            condition=get_description(weather_code),
        )
        for d, high, low, weather_code,precipitation_probability in zip(dates, highs, lows, weather_codes, precipitation_probabilities, strict=True)
    )

def _local_times(group, count, tz):
    return [
        datetime.fromtimestamp(group.Time() + i * group.Interval(), tz=tz)
        for i in range(count)
    ]