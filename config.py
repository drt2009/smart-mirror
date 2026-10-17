from dotenv import load_dotenv
import os

def load_location() -> tuple[float, float]:
    load_dotenv()
    lat = _read_float("LATITUDE", -90, 90)
    lon = _read_float("LONGITUDE", -180, 180)
    return lat, lon

def load_location_name() -> str|None:
    load_dotenv()
    return os.getenv("LOCATION_NAME")

def _read_float(name, low, high):
    raw = os.environ.get(name)
    if not raw:
        raise ValueError(f"{name} is not set")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}, got {value}")
    return value