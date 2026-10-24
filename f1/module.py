import queue
import threading
import tkinter as tk
from datetime import datetime, timezone

from f1.client import F1FetchError, fetch_next_race
from f1.state import F1State
from f1.views import f1_lines

POLL_MS = 500
REFRESH_MS = 15 * 60 * 1000
RENDER_MS = 60 * 1000
STALE_AFTER_SECONDS = 60 * 60


class F1Module(tk.Frame):
    def __init__(self, parent, tz):
        super().__init__(parent)
        self.config(bg="black")
        self._tz = tz
        self._state = F1State(stale_after=STALE_AFTER_SECONDS)
        self._results = queue.Queue()
        self._fetching = False
        self._f1_label = tk.Label(self, bg="black", fg="white",
                                  font=("Arial", 28), anchor="sw", justify="left")
        self._f1_label.pack(anchor="sw")
        self._render()
        self._refresh()
        self.after(POLL_MS, self._poll)
        self.after(RENDER_MS, self._tick)

    def _refresh(self):
        if not self._fetching:
            self._fetching = True
            threading.Thread(target=self._fetch_worker, daemon=True).start()
        self.after(REFRESH_MS, self._refresh)

    def _fetch_worker(self):
        try:
            self._results.put(fetch_next_race())
        except F1FetchError as error:
            self._results.put(error)

    def _poll(self):
        if not self._results.empty():
            result = self._results.get()
            self._fetching = False
            if isinstance(result, F1FetchError):
                self._state.mark_failed()
            else:
                self._state.update(result)
            self._render()
        self.after(POLL_MS, self._poll)

    def _tick(self):
        self._render()
        self.after(RENDER_MS, self._tick)

    def _render(self):
        lines = f1_lines(self._state, datetime.now(timezone.utc), self._tz)
        self._f1_label.config(text="\n".join(lines))