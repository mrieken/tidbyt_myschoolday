from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tidbyt_timetable.schedule import is_publish_time, should_publish

BERLIN = ZoneInfo("Europe/Berlin")


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(6, 29, False), (6, 30, True), (7, 59, True), (8, 0, False), (8, 7, False)],
)
def test_publish_window_boundaries(hour, minute, expected):
    now = datetime(2026, 11, 3, hour, minute, tzinfo=BERLIN)
    assert is_publish_time(now) is expected


def test_publish_requires_a_valid_school_day():
    now = datetime(2026, 11, 3, 6, 30, tzinfo=BERLIN)
    assert should_publish(now, school_day=True)
    assert not should_publish(now, school_day=False)


@pytest.mark.parametrize(
    ("utc_hour", "utc_minute", "expected_local_hour", "expected_offset"),
    [(4, 35, 6, 2), (5, 35, 6, 1)],
)
def test_dst_offsets_are_converted_to_berlin(utc_hour, utc_minute, expected_local_hour, expected_offset):
    utc = ZoneInfo("UTC")
    day = datetime(2026, 3, 29, utc_hour, utc_minute, tzinfo=utc) if expected_offset == 2 else datetime(2026, 10, 25, utc_hour, utc_minute, tzinfo=utc)

    local = day.astimezone(BERLIN)
    assert local.hour == expected_local_hour
    assert local.utcoffset().total_seconds() == expected_offset * 3600
    assert is_publish_time(day)


def test_naive_clock_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        is_publish_time(datetime(2026, 11, 3, 6, 30))