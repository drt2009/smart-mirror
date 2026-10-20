import asyncio


from ical.calendar_stream import IcsCalendarStream


class CalendarFetchError(Exception):
    pass

async def fetch_calendar_text(url:str):
    return await IcsCalendarStream.calendar_from_url(url)