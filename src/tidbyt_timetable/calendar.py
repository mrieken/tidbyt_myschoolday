"""Offline Niedersachsen school-day calendar with explicit coverage bounds."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import holidays

from tidbyt_timetable.config import ConfigurationError, _parse_date, _read_yaml


class CalendarCoverageError(ValueError):
    """Raised when the official school-holiday dataset does not cover a date."""


@dataclass(frozen=True)
class HolidayRange:
    name: str
    start: date
    end: date

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True)
class SchoolCalendar:
    coverage_start: date
    coverage_end: date
    ranges: tuple[HolidayRange, ...]
    additional_days_off: frozenset[date] = frozenset()

    @classmethod
    def from_file(cls, path: Path, additional_days_off: frozenset[date] = frozenset()) -> SchoolCalendar:
        data = _read_yaml(path)
        if not isinstance(data, dict):
            raise ConfigurationError("Holiday calendar must be a YAML mapping")
        if not isinstance(data.get("source"), str) or not data["source"].startswith("https://"):
            raise ConfigurationError("Holiday calendar must include its official source URL")
        coverage_start = _parse_date(data.get("coverage_start"), "coverage_start")
        coverage_end = _parse_date(data.get("coverage_end"), "coverage_end")
        if coverage_start > coverage_end:
            raise ConfigurationError("coverage_start must be on or before coverage_end")

        raw_ranges = data.get("ranges")
        if not isinstance(raw_ranges, list) or not raw_ranges:
            raise ConfigurationError("Holiday calendar ranges must be a non-empty list")
        ranges: list[HolidayRange] = []
        for index, value in enumerate(raw_ranges):
            field = f"ranges[{index}]"
            if not isinstance(value, dict) or not isinstance(value.get("name"), str) or not value["name"].strip():
                raise ConfigurationError(f"{field} must include a non-empty name")
            start = _parse_date(value.get("start"), f"{field}.start")
            end = _parse_date(value.get("end"), f"{field}.end")
            if start > end:
                raise ConfigurationError(f"{field}.start must be on or before {field}.end")
            if start < coverage_start or end > coverage_end:
                raise ConfigurationError(f"{field} falls outside declared calendar coverage")
            ranges.append(HolidayRange(value["name"], start, end))

        ordered_ranges = sorted(ranges, key=lambda item: (item.start, item.end))
        for previous, current in zip(ordered_ranges, ordered_ranges[1:]):
            if current.start <= previous.end:
                warnings.warn(
                    f"Holiday ranges overlap: {previous.name!r} and {current.name!r}",
                    stacklevel=2,
                )
        return cls(coverage_start, coverage_end, tuple(ordered_ranges), additional_days_off)

    def is_school_day(self, day: date) -> bool:
        if day < self.coverage_start or day > self.coverage_end:
            raise CalendarCoverageError(
                f"Official school-holiday calendar covers {self.coverage_start} through "
                f"{self.coverage_end}; refusing to assume {day} is a school day"
            )
        if day.weekday() >= 5 or day in self.additional_days_off:
            return False
        if any(holiday_range.contains(day) for holiday_range in self.ranges):
            return False
        return day not in _niedersachsen_public_holidays(day.year)


@lru_cache(maxsize=32)
def _niedersachsen_public_holidays(year: int) -> holidays.HolidayBase:
    return holidays.country_holidays("DE", subdiv="NI", years=[year])