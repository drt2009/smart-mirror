import tkinter as tk
from datetime import date
import queue
import threading

from weather.state import WeatherState
from weather.client import fetch_weather, WeatherFetchError
import weather.views as views


class WeatherModule(tk.Frame):
    def __init__(self, parent, lat, lon, loc_name):
        super().__init__(parent, bg="black")
        self._weather_label = tk.Label(self, text="Loading.",
                        bg="black", fg="white",
                        font=("Arial", 28), anchor="nw"
                        )
        self._weather_label.pack(anchor="nw")
        self._weather_state = WeatherState(600)
        self._lat = lat
        self._lon = lon
        self._fetch_snapshot(self._lat, self._lon)
        self._location_name = loc_name
        self._results = queue.Queue()

        self._render()
        self._start_fetch()
        self.after(500, self._poll)
        self.after(3000, self._rotation)


    def _start_fetch(self):
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
            self._results.put(fetch_weather(self._lat, self._lon))
        except WeatherFetchError as error:
            self._results.put(error)


    def _poll(self):
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            pass
        else:
            if isinstance(result, WeatherFetchError):
                self._weather_state.mark_failed()
                next_fetch_ms = 60 * 1000
            else:
                self._weather_state.update(result)
                next_fetch_ms = 10 * 60 * 1000
            self._render()
            self.after(next_fetch_ms, self._start_fetch)
        self.after(500, self._poll)

    def _rotation(self):
        self._weather_state.advance()
        self._render()
        self.after(3000, self._rotation)

    def _render(self):
        if self._weather_state.is_loading:
            self._weather_label = self._is_loading_text()
        else:
            self._current_view_text()

    def _is_loading_text(self):
        return  self._weather_label.config(text="Loading...")

    def _current_view_text(self):
        match self._weather_state.view:
            case "current" :
                 return self._weather_label.config(
                     text=self._location_name+"\n"+"\n".join(views.current_view(self._weather_state.snapshot)))
            case "hourly":
                return self._weather_label.config(
                    text=self._location_name + "\n" + "\n".join(views.hourly_view(self._weather_state.snapshot)))
            case "daily":
                return self._weather_label.config(
                    text=self._location_name + "\n" + "\n".join(views.daily_view(self._weather_state.snapshot,date.today())))
            case _:
                raise NotImplementedError

    def _fetch_snapshot(self, lat, lon):
        self._weather_state.update(fetch_weather(lat, lon))