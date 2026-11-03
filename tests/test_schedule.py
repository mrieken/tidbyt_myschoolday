from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tidbyt_timetable.schedule import BERLIN, berlin_now

BERLIN = ZoneInfo("Europe/Berlin")


@pytest.mark.parametrize(
    ("utc_hour", "utc_minute", "expected_local_hour", "expected_offset"),
    [(4, 35, 6, 2), (5, 35, 6, 1)],
)
def test_dst_offsets_are_converted_to_berlin(utc_hour, utc_minute, expected_local_hour, expected_offset):
    utc = ZoneInfo("UTC")
    day = datetime(2026, 3, 29, utc_hour, utc_minute, tzinfo=utc) if expected_offset == 2 else datetime(2026, 10, 25, utc_hour, utc_minute, tzinfo=utc)

    local = berlin_now(day)
    assert local.hour == expected_local_hour
    assert local.utcoffset().total_seconds() == expected_offset * 3600


def test_naive_clock_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        berlin_now(datetime(2026, 11, 3, 6, 30))