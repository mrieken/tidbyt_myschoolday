"""Pure time-window rules for scheduled publication."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

PUBLISH_START = time(6, 30)
PUBLISH_END = time(8, 0)
BERLIN = ZoneInfo("Europe/Berlin")


def berlin_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(BERLIN)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("The scheduling clock must be timezone-aware")
    return current.astimezone(BERLIN)


def is_publish_time(now: datetime | None = None) -> bool:
    local_now = berlin_now(now)
    return PUBLISH_START <= local_now.time().replace(tzinfo=None) < PUBLISH_END


def should_publish(now: datetime, school_day: bool) -> bool:
    return school_day and is_publish_time(now)