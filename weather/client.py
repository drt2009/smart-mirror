from weather.codes import get_description
from weather.models import CurrentWeather, WeatherSnapshot
from weather.variables import CurrentIdx

def parse(response):
    return WeatherSnapshot(
        current= _parse_current(response),
        hourly= _parse_hourly(response),
        daily= (),
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

def _parse_hourly(response):
    return ()