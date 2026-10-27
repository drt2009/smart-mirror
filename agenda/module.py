import asyncio
import tkinter as tk
from datetime import datetime
import queue
import threading
from zoneinfo import ZoneInfo

from agenda.client import CalendarFetchError, fetch_calendar
from agenda.state import AgendaState
from agenda.views import agenda_rows
from agenda.parse import upcoming


class AgendaModule(tk.Frame):
    _TZ = ZoneInfo("America/New_York")
    _STALE_AFTER_SECONDS = 900
    _REFRESH_MS = 10 * 60 * 1000
    _RETRY_MS = 60 * 1000
    _POLL_MS = 500
    _FONT = ("Arial", 28)

    def __init__(self, parent, ical_address):
        super().__init__(parent, bg ="black")
        self._message_label = tk.Label(self, text="Loading...",
                        bg="black", fg="white",
                        font=self._FONT, anchor="ne"
                        )
        self._message_label.pack(anchor="nw")
        self._rows_frame = tk.Frame(self, bg="black")

        self._agende_state = AgendaState(self._STALE_AFTER_SECONDS)
        self._ical_address = ical_address

        self._results = queue.Queue()
        self._render()
        self._start_fetch()
        self.after(self._POLL_MS, self._poll)

    def _start_fetch(self):
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
           calendar = asyncio.run(fetch_calendar(self._ical_address))
           result = upcoming(calendar, datetime.today().astimezone(self._TZ))
           self._results.put(result)
        except CalendarFetchError as error:
            self._results.put(error)

    def _poll(self):
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            pass
        else:
            if isinstance(result, CalendarFetchError):
                self._agende_state.mark_failed()
                next_fetch_ms = self._RETRY_MS
            else:
                self._agende_state.update(result)
                next_fetch_ms = self._REFRESH_MS
            self._render()
            self.after(next_fetch_ms, self._start_fetch)
        self.after(self._POLL_MS, self._poll)

    def _render(self):
        if self._agende_state.is_loading:
            self._message_label.config(text="Loading...")
        else:
            now = datetime.now(self._TZ)
            rows = agenda_rows(self._agende_state.events, now, self._TZ)
            self._show_rows(rows)

    def _update_to_loading(self, message:str):
        self._clear_rows()
        self._rows_frame.pack_forget()
        self._message_label.config(text=message)
        self._message_label.pack(anchor="ne")

    def _clear_rows(self):
        for child in self._rows_frame.winfo_children():
            child.destroy()

    def _show_rows(self, rows):
        self._message_label.pack_forget()
        self._clear_rows()
        self._rows_frame.pack(anchor="ne", padx=(0,15))
        for row_number, row in enumerate(rows):
            for column_number, text in enumerate(row):
                wrap = 450 if column_number == 2 else 0
                tk.Label(self._rows_frame, text=text, bg="black", fg="white",
                         font=self._FONT, anchor="w", justify="left",
                         wraplength=wrap,
                         ).grid(row=row_number, column=column_number,
                                sticky="nw", padx=(0, 16))
