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

def load_calendar_url() -> str|None:
    load_dotenv()
    calendar_url = os.getenv("SECRET_ICAL_URL")
    if calendar_url:
        calendar_url = calendar_url.strip()
        if calendar_url:
            return calendar_url
        else:
            raise ValueError("SECRET_ICAL_URL is not set")
    else:
        raise ValueError("SECRET_ICAL_URL is not set")