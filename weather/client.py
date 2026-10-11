from weather.codes import get_description
from weather.models import CurrentWeather, HourlyEntry, DailyEntry, WeatherSnapshot
from weather.variables import CurrentIdx, HourlyIdx, DailyIdx
from datetime import datetime, timedelta, timezone

def parse(response) -> WeatherSnapshot:
    tz = timezone(timedelta(seconds=response.UtcOffsetSeconds()))
    return WeatherSnapshot(
        current= _parse_current(response),
        hourly= _parse_hourly(response,tz),
        daily= _parse_daily(response,tz)
    )

def _parse_current(response):
    current = response.Current()
    current_weather_code = int(current.Variables(CurrentIdx.WEATHER_CODE).Value())

    return CurrentWeather(
        temperature=float(current.Variables(CurrentIdx.TEMPERATURE_2M).Value()),
        feels_like=float(current.Variables(CurrentIdx.APPARENT_TEMPERATURE).Value()),
        weather_code=current_weather_code,
        condition=get_description(current_weather_code),
    )

def _parse_hourly(response, tz):
    hourly = response.Hourly()
    temperatures = hourly.Variables(HourlyIdx.TEMPERATURE_2M).ValuesAsNumpy()
    feel_likes = hourly.Variables(HourlyIdx.APPARENT_TEMPERATURE).ValuesAsNumpy()
    weather_codes = hourly.Variables(HourlyIdx.WEATHER_CODE).ValuesAsNumpy()
    precipitation_probabilities = hourly.Variables(HourlyIdx.PRECIPITATION_PROBABILITY).ValuesAsNumpy()
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
    highs = daily.Variables(DailyIdx.TEMPERATURE_2M_MAX).ValuesAsNumpy()
    lows = daily.Variables(DailyIdx.TEMPERATURE_2M_MIN).ValuesAsNumpy()
    weather_codes = daily.Variables(DailyIdx.WEATHER_CODE).ValuesAsNumpy()
    precipitation_probabilities = daily.Variables(DailyIdx.PRECIPITATION_PROBABILITY_MEAN).ValuesAsNumpy()
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