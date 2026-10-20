from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime
    end: datetime
