from datetime import date
from pathlib import Path

import pytest

from tidbyt_timetable.calendar import CalendarCoverageError, SchoolCalendar
from tidbyt_timetable.config import ConfigurationError, load_timetable

ROOT = Path(__file__).parents[1]
TIMETABLE_PATH = ROOT / "config" / "timetable.yaml"
HOLIDAYS_PATH = ROOT / "config" / "holidays_ni.yaml"


@pytest.fixture
def calendar():
    timetable = load_timetable(TIMETABLE_PATH)
    return SchoolCalendar.from_file(HOLIDAYS_PATH, timetable.additional_days_off)


def test_weekends_are_not_school_days(calendar):
    assert not calendar.is_school_day(date(2026, 11, 1))
    assert not calendar.is_school_day(date(2026, 10, 31))
    assert calendar.is_school_day(date(2026, 11, 2))


@pytest.mark.parametrize("day", [date(2026, 7, 2), date(2026, 7, 20), date(2026, 8, 12)])
def test_summer_holiday_bounds_are_inclusive(calendar, day):
    assert not calendar.is_school_day(day)


def test_individual_non_contiguous_day_is_a_holiday(calendar):
    assert not calendar.is_school_day(date(2026, 5, 15))


def test_regional_public_holiday_is_excluded(calendar):
    assert not calendar.is_school_day(date(2025, 10, 31))


def test_manual_day_off_is_excluded():
    calendar = SchoolCalendar(date(2026, 1, 1), date(2026, 12, 31), (), frozenset({date(2026, 11, 2)}))
    assert not calendar.is_school_day(date(2026, 11, 2))


def test_outside_coverage_fails_closed(calendar):
    with pytest.raises(CalendarCoverageError, match="refusing to assume"):
        calendar.is_school_day(date(2030, 9, 2))


def test_invalid_holiday_range_is_rejected(tmp_path):
    config = tmp_path / "holidays.yaml"
    config.write_text(
        'source: "https://example.invalid/calendar"\n'
        'coverage_start: "2026-01-01"\n'
        'coverage_end: "2026-12-31"\n'
        'ranges:\n  - name: Invalid\n    start: "2026-02-01"\n    end: "2026-01-01"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="on or before"):
        SchoolCalendar.from_file(config)


def test_missing_coverage_bound_is_rejected(tmp_path):
    config = tmp_path / "holidays.yaml"
    config.write_text(
        'source: "https://example.invalid/calendar"\n'
        'coverage_start: "2026-01-01"\n'
        'ranges:\n  - name: Example\n    start: "2026-02-01"\n    end: "2026-02-02"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="coverage_end"):
        SchoolCalendar.from_file(config)