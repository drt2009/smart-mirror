from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UpcomingRace:
    circuit_name: str
    country:str
    race_date: datetime
    sprint_race:bool