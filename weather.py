import tkinter as tk
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from openMeteoWatherCode import OpenMeteoWeatherCode as weatherCode



class WeatherModule(tk.Frame):
  def __init__(self, parent):
    tk.Frame.__init__(self, parent)

    header = tk.Label(self, text="Weather",
                      font=("Arial", 28, "bold"),
                      bg="black", fg="white")
    header.pack(anchor="w")

    self.configure(background="black")


    self.current_temp_label = tk.Label(self,
                      font=("Arial", 28),
                      fg="white", bg="black")
    self.current_temp_label.pack()

    self.current_weather_label = tk.Label(self,
                      font=("Arial", 14),
                      fg="white", bg="black")
    self.current_weather_label.pack()


    self.update_weather()

  def update_weather(self):
    response = self.get_weather_data()
    current = response.Current()
    current_temperature = f"{round(current.Variables(0).Value())}°F"
    self.current_temp_label.config(text=current_temperature)

    current_weather_code = current.Variables(2).Value()
    self.current_weather_label.config(text=weatherCode.get_description(current_weather_code))

  def get_weather_data(self):
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
      "latitude": 0,
      "longitude": 0,
      "daily": ["weather_code", "uv_index_max", "temperature_2m_max",
                "temperature_2m_min", "rain_sum", "showers_sum",
                "snowfall_sum", "precipitation_sum", "moon_phase"],
      "hourly": ["temperature_2m", "apparent_temperature", "weather_code",
                 "precipitation_probability", "precipitation", "rain",
                 "showers", "snowfall", "snow_depth"],
      "current": ["temperature_2m", "apparent_temperature", "weather_code",
                  "cloud_cover", "precipitation", "rain", "showers",
                  "snowfall"],
      "timezone": "America/New_York",
      "forecast_days": 3,
      "forecast_hours": 4,
      "wind_speed_unit": "mph",
      "temperature_unit": "fahrenheit",
      "precipitation_unit": "inch",
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    return response
