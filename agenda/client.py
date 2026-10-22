import asyncio

from ical.calendar_stream import IcsCalendarStream

DEFAULT_TIMEOUT_SECONDS = 30.0

class CalendarFetchError(Exception):
    pass

async def fetch_calendar(url:str, timeout=DEFAULT_TIMEOUT_SECONDS):
    if timeout<=0:
        raise CalendarFetchError("Timeout error")
    try:
        return await asyncio.wait_for(IcsCalendarStream.calendar_from_url(url),timeout)
    except Exception:
        raise CalendarFetchError("could not fetch the calendar") from None