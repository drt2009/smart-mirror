import time

from weather.models import WeatherSnapshot

VIEWS = ("current", "hourly", "daily")

class WeatherState:

    def __init__(self, stale_after : int , clock =time.monotonic):
        self._clock = clock
        if stale_after <= 0:
            raise ValueError
        self._stale_after = stale_after
        self._current_view = "current"
        self._internal_snapshot = None
        self._updated_at = None
        self._last_failed = False

    def update(self, snapshot: WeatherSnapshot):
        self._internal_snapshot = snapshot
        self._updated_at = self._clock()
        self._last_failed = False

    def advance(self):
        current_view_index = VIEWS.index(self._current_view)
        self._current_view = VIEWS[(current_view_index+1)%len(VIEWS)]
        return self._current_view

    def mark_failed(self):
        self._last_failed = True

    @property
    def is_stale(self):
        if self._updated_at is None:
            return False
        return self._clock() - self._updated_at > self._stale_after

    @property
    def last_fetch_failed(self):
        return self._last_failed

    @property
    def is_loading(self):
        return self.snapshot is None

    @property
    def view(self):
        return self._current_view

    @property
    def snapshot(self):
        return self._internal_snapshot