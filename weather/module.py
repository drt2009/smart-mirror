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
    _MAX_COLUMNS = 5
    _MAX_ROWS = 4
    _WIDTH_PX = 700
    _HEIGHT_PX = 340
    _WRAP_PX = 450
    _FONT = ("Arial", 28)

    def __init__(self, parent, lat, lon, loc_name):
        super().__init__(parent, bg="black", width=self._WIDTH_PX, height=self._HEIGHT_PX)
        self.pack_propagate(False)

        self._header = tk.Label(self, text=loc_name, bg="black", fg="white", font=self._FONT)
        self._body_label = tk.Label(self, bg="black", fg="white", font=self._FONT, justify="center")
        self._rows_frame = tk.Frame(self, bg="black")
        self._cells = self._build_cells()
        self._header.pack(fill="x")
        self._shown = None

        self._weather_state = WeatherState(self._STALE_AFTER_SECONDS)
        self._lat = lat
        self._lon = lon
        self._results = queue.Queue()

        self._render()
        self._start_fetch()
        self.after(self._POLL_MS, self._poll)
        self.after(self._ROTATE_MS, self._rotation)

    def _build_cells(self):
        cells = []
        for row_number in range(self._MAX_ROWS):
            cell_row = []
            for column_number in range(self._MAX_COLUMNS):
                cell = tk.Label(self._rows_frame, bg="black", fg="white", font=self._FONT,
                                anchor="w", justify="left", wraplength=self._WRAP_PX)
                cell.grid(row=row_number, column=column_number, sticky="nw", padx=(0, 16))
                cell.grid_remove()
                cell_row.append(cell)
            cells.append(cell_row)
        return cells

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
            self._show_text("Loading...")
        else:
            self._current_view_text()

    def _current_view_text(self):
        snapshot = self._weather_state.snapshot
        match self._weather_state.view:
            case "current":
                self._show_text("\n".join(views.current_view(snapshot)))
            case "hourly":
                self._show_rows(views.hourly_rows(snapshot))
            case "daily":
                self._show_rows(views.daily_rows(snapshot, date.today()))
            case _:
                raise NotImplementedError

    def _show_text(self, text):
        if self._shown == ("text", text):
            return
        self._shown = ("text", text)
        self._rows_frame.pack_forget()
        self._body_label.config(text=text)
        self._body_label.pack()

    def _show_rows(self, rows):
        if self._shown == ("rows", rows):
            return
        self._shown = ("rows", rows)
        self._body_label.pack_forget()
        self._rows_frame.pack()
        for row_number, cell_row in enumerate(self._cells):
            for column_number, cell in enumerate(cell_row):
                if row_number < len(rows) and column_number < len(rows[row_number]):
                    cell.config(text=rows[row_number][column_number])
                    cell.grid()
                else:
                    cell.grid_remove()