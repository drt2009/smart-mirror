import asyncio
import tkinter as tk
from datetime import date
import queue
import threading

from agenda.clent import CalendarFetchError
from agenda.state import AgendaState
from agenda.clent import fetch_calendar_text
from agenda.view import agenda_view


class AgendaModule(tk.Frame):

    _STALE_AFTER_SECONDS = 600
    _REFRESH_MS = 10 * 60 * 1000
    _RETRY_MS = 60 * 1000
    _POLL_MS = 500

    def __init__(self, parent, ical_address):
        super().__init__(parent, bg ="black")
        self._agenda_label = tk.Label(self, text="Loading....",
                        bg="black", fg="white",
                        font=("Arial", 28), anchor="ne"
                        )
        self._agenda_label.pack(anchor="ne")

        self._agende_state = AgendaState(600)
        self._ical_address = ical_address

        self._results = queue.Queue()
        self._render()
        self._start_fetch()
        self.after(self._POLL_MS, self._poll)

    def _start_fetch(self):
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
           result = asyncio.run(fetch_calendar_text(self._ical_address))
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
                self._agende_state.update_calendar(result)
                next_fetch_ms = self._REFRESH_MS
            self._render()
            self.after(next_fetch_ms, self._start_fetch)
        self.after(self._POLL_MS, self._poll)

    def _render(self):
        if self._agende_state.is_loading:
            self._agenda_label.config(text="Loading...")
        else:
            self._agenda_text()
        self.after(200, self._render)

    def _agenda_text(self):
        self._agenda_label.config(
            text="\n".join(agenda_view(self._agende_state.ics_calendar_events))
        )