import time

class AgendaState:
    def __init__(self, stale_after : int ,  clock =time.monotonic):
        self._clock = clock
        if stale_after <= 0:
            raise ValueError("stale_after must be positive")
        self._stale_after = stale_after
        self._updated_at = None
        self._last_failed = False
        self._events = []

    def update(self, events:list):
       self._events = events.copy()
       self._updated_at = self._clock()
       self._last_failed = False

    def mark_failed(self):
        self._last_failed = True

    @property
    def last_fetch_failed(self):
        return self._last_failed

    @property
    def is_loading(self):
        return self.events == [] and self._updated_at is None

    @property
    def is_stale(self):
        if self._updated_at is None:
            return False
        return self._clock() - self._updated_at > self._stale_after

    @property
    def events(self):
        return self._events.copy()