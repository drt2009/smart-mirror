import tkinter as tk
from datetime import date
import queue
import threading

from weather.state import WeatherState
from weather.client import fetch_weather, WeatherFetchError
import weather.views as views


class WeatherModule(tk.Frame):

    _STALE_AFTER_SECONDS = 600
    _ROTATE_MS = 2_000
    _REFRESH_MS = 10 * 60 * 1000
    _RETRY_MS = 60 * 1000
    _POLL_MS = 500
    _COLUMNS = 5
    _TABLE_WIDTH_PX = 700
    _TABLE_HEIGHT_PX = 340

    def __init__(self, parent, lat, lon, loc_name):
        super().__init__(parent, bg="black")
        self._weather_label = tk.Label(self, text="Loading....",
                        bg="black", fg="white",
                        font=("Arial", 28), anchor="nw"
                        )
        self._weather_label.pack(anchor="nw")

        self._rows_frame = tk.Frame(self, bg="black",
                                    width=self._TABLE_WIDTH_PX, height=self._TABLE_HEIGHT_PX)
        self._rows_frame.grid_propagate(False)
        self._rows_frame.grid_columnconfigure(0, weight=1)
        self._rows_frame.grid_columnconfigure(self._COLUMNS + 1, weight=1)


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
            self._string_view("Loading...")
        else:
            self._current_view_text()

    def _current_view_text(self):
        match self._weather_state.view:
            case "current" :
                lines = views.current_view(self._weather_state.snapshot)
                self._show_rows([[line] for line in lines], header=self._location_name)
            case "hourly":
                self._show_rows(views.hourly_rows(self._weather_state.snapshot), self._location_name)
            case "daily":
                self._show_rows(views.daily_rows(self._weather_state.snapshot, date.today()),self._location_name)
            case _:
                raise NotImplementedError

    def _clear_rows(self):
        for child in self._rows_frame.winfo_children():
            child.destroy()

    def _string_view(self, message):
        self._clear_rows()
        self._rows_frame.pack_forget()
        self._weather_label.config(text=message)
        self._weather_label.pack(anchor="center")

    def _show_rows(self, rows,  header=None):
        self._weather_label.pack_forget()
        self._clear_rows()
        self._rows_frame.pack(anchor="ne")
        first_row = 0
        if header is not None:
            max((len(row) for row in rows), default=1)
            tk.Label(self._rows_frame, text=header, bg="black", fg="white",
                     font=("Arial", 28), anchor="center",
                     ).grid(row=0, column=0, columnspan=self._COLUMNS+2, sticky="ew")
            first_row = 1

        for row_number, row in enumerate(rows, start=first_row):
            for column_number, text in enumerate(row):
                wrap = 450 if column_number == 2 else 0
                tk.Label(self._rows_frame, text=text, bg="black", fg="white",
                         font=("Arial", 28), anchor="w", justify="left",
                         wraplength=wrap,
                         ).grid(row=row_number, column=column_number+1,
                                sticky="nw", padx=(0, 16))
