"""Berlin clock helpers for scheduled operations."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def berlin_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(BERLIN)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("The clock must be timezone-aware")
    return current.astimezone(BERLIN)