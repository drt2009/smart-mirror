import tkinter as tk
from datetime import date
import queue
import threading

from weather.state import WeatherState
from weather.client import fetch_weather, WeatherFetchError
import weather.views as views


class WeatherModule(tk.Frame):

    _STALE_AFTER_SECONDS = 600
    _ROTATE_MS = 20_000
    _REFRESH_MS = 10 * 60 * 1000
    _RETRY_MS = 60 * 1000
    _POLL_MS = 500

    def __init__(self, parent, lat, lon, loc_name):
        super().__init__(parent, bg="black")
        self._weather_label = tk.Label(self, text="Loading....",
                        bg="black", fg="white",
                        font=("Arial", 28), anchor="nw"
                        )
        self._weather_label.pack(anchor="nw")
        self._weather_state = WeatherState(600)
        self._lat = lat
        self._lon = lon
        self._location_name = loc_name
        self._results = queue.Queue()

        self._render()
        self._start_fetch()
        self.after(self._POLL_MS, self._poll)
        self.after(self._ROTATE_MS, self._rotation)


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
                next_fetch_ms = self._RETRY_MS
            else:
                self._weather_state.update(result)
                next_fetch_ms = self._REFRESH_MS
            self._render()
            self.after(next_fetch_ms, self._start_fetch)
        self.after(self._POLL_MS, self._poll)

    def _rotation(self):
        self._weather_state.advance()
        self._render()
        self.after(self._ROTATE_MS, self._rotation)

    def _render(self):
        if self._weather_state.is_loading:
            self._weather_label.config(text="Loading...")
        else:
            self._current_view_text()

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
