import queue
import threading
import tkinter as tk

from f1.client import fetch_next_race
from f1.views import upcoming_race_view


class F1Module(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config(bg="black")
        upcoming_race_view
        self._f1_label = tk.Label(self, text="Loading....",
                        bg="black", fg="white",
                        font=("Arial", 28), anchor="sw"
                        )
        self._f1_label.pack(anchor="sw")
        self._results = queue.Queue()
        self._upcoming_view = None
        self._start_fetch()
        self.after(500, self._poll)

    def _start_fetch(self):
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
            self._results.put(fetch_next_race())
        except Exception as error:
            self._results.put(error)
    def _poll(self):
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            pass
        else:
            if isinstance(result, Exception):
                pass
            else:
                self._upcoming_view = upcoming_race_view(result)
            self._render()
        self.after(500, self._poll)


    def _render(self):
        if self._upcoming_view is None:
            self._f1_label.config(text="Loading...")
        else:
            self._f1_label.config(text= "\n".join(self._upcoming_view))