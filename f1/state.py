import time


class F1State:
    def __init__(self, stale_after, clock=time.monotonic):
        if stale_after <= 0:
            raise ValueError ("stale_after must be positive")
        self._stale_after = stale_after
        self._clock = clock
        self._race = None
        self._updated_at = None
        self._last_failed = False
        self._is_loading = True

    def update(self, race):
        self._race = race
        self._updated_at = self._clock()
        self._last_failed = False
        self._is_loading = False

    def mark_failed(self):
        self._last_failed = True

    @property
    def is_loading(self):
        return self._is_loading

    @property
    def last_fetch_failed(self):
        return self._last_failed

    @property
    def is_stale(self):
        if self._updated_at is None:
            return False
        return self._clock() - self._updated_at > self._stale_after

    @property
    def race(self):
        return self._race