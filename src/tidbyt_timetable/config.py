"""Loading and validation for the human-editable YAML configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from tidbyt_timetable.renderer import DisplayLesson, FONT, UNKNOWN_COLOR, WIDTH

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")
COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}\Z")
ABBREVIATION_PATTERN = re.compile(r"[A-Z0-9-]{1,3}\Z")


class ConfigurationError(ValueError):
    """Raised when a timetable or holiday YAML file is invalid."""


@dataclass(frozen=True)
class Subject:
    abbreviation: str
    color: tuple[int, int, int]


@dataclass(frozen=True)
class TimetableConfig:
    timezone: ZoneInfo
    installation_id: str
    weekly_timetable: dict[str, tuple[str, ...]]
    subjects: dict[str, Subject]
    additional_days_off: frozenset[date]

    def lessons_for_date(self, school_date: date) -> tuple[DisplayLesson, ...]:
        names = self.weekly_timetable[WEEKDAYS[school_date.weekday()]]
        return tuple(
            DisplayLesson(
                name=name,
                color=self.subjects[name].color if name else UNKNOWN_COLOR,
            )
            for name in names
        )


def _read_yaml(path: Path) -> object:
    try:
        with path.open(encoding="utf-8") as file:
            return yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(f"Cannot read configuration {path}: {error}") from error


def _parse_date(value: object, field: str) -> date:
    if isinstance(value, datetime):
        raise ConfigurationError(f"{field} must be a date without a time")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ConfigurationError(f"{field} must use YYYY-MM-DD format") from error
        if parsed.isoformat() != value:
            raise ConfigurationError(f"{field} must use YYYY-MM-DD format")
        return parsed
    raise ConfigurationError(f"{field} must be a date in YYYY-MM-DD format")


def load_timetable(path: Path) -> TimetableConfig:
    data = _read_yaml(path)
    if not isinstance(data, dict):
        raise ConfigurationError("Timetable configuration must be a YAML mapping")

    timezone_name = data.get("timezone")
    if timezone_name != "Europe/Berlin":
        raise ConfigurationError("timezone must be Europe/Berlin")
    try:
        timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, TypeError) as error:
        raise ConfigurationError(f"Unknown timezone: {timezone_name}") from error

    installation_id = data.get("installation_id")
    if installation_id != "schooltimetable":
        raise ConfigurationError("installation_id must remain schooltimetable (Tidbyt IDs are alphanumeric)")

    raw_subjects = data.get("subjects")
    if not isinstance(raw_subjects, dict) or not raw_subjects:
        raise ConfigurationError("subjects must be a non-empty mapping")
    subjects: dict[str, Subject] = {}
    for name, value in raw_subjects.items():
        if not isinstance(name, str) or not name or not isinstance(value, dict):
            raise ConfigurationError("Each subject must have a name and a mapping of display settings")
        unsupported_characters = sorted(set(name.upper()) - FONT.keys())
        if unsupported_characters:
            raise ConfigurationError(f"Subject {name!r} contains unsupported display characters: {unsupported_characters}")
        if len(name) * 4 - 1 > WIDTH - 15:
            raise ConfigurationError(f"Subject {name!r} is too long to fit on the display")
        abbreviation = value.get("abbreviation")
        if not isinstance(abbreviation, str) or not ABBREVIATION_PATTERN.fullmatch(abbreviation):
            raise ConfigurationError(f"Subject {name!r} abbreviation must be 1-3 uppercase letters, digits, or hyphens")
        color_text = value.get("color")
        if not isinstance(color_text, str) or not COLOR_PATTERN.fullmatch(color_text):
            raise ConfigurationError(f"Subject {name!r} color must use #RRGGBB format")
        color = tuple(int(color_text[index:index + 2], 16) for index in (1, 3, 5))
        subjects[name] = Subject(abbreviation, color)

    raw_weekly = data.get("weekly_timetable")
    if not isinstance(raw_weekly, dict):
        raise ConfigurationError("weekly_timetable must be a mapping")
    missing_days = set(WEEKDAYS) - raw_weekly.keys()
    extra_days = raw_weekly.keys() - set(WEEKDAYS)
    if missing_days or extra_days:
        raise ConfigurationError(
            f"weekly_timetable must contain exactly {', '.join(WEEKDAYS)}; "
            f"missing={sorted(missing_days)}, unexpected={sorted(extra_days)}"
        )
    weekly_timetable: dict[str, tuple[str, ...]] = {}
    for weekday in WEEKDAYS:
        lessons = raw_weekly[weekday]
        if not isinstance(lessons, list) or len(lessons) != 5:
            count = len(lessons) if isinstance(lessons, list) else "not a list"
            raise ConfigurationError(f"{weekday} must contain exactly five lesson slots, got {count}")
        if any(not isinstance(lesson, str) for lesson in lessons):
            raise ConfigurationError(f"{weekday} lesson names must be strings; use an empty string for unknown lessons")
        unknown = sorted({lesson for lesson in lessons if lesson and lesson not in subjects})
        if unknown:
            raise ConfigurationError(f"{weekday} contains unknown subjects: {', '.join(unknown)}")
        weekly_timetable[weekday] = tuple(lessons)

    raw_days_off = data.get("additional_days_off", [])
    if not isinstance(raw_days_off, list):
        raise ConfigurationError("additional_days_off must be a list of YYYY-MM-DD dates")
    days_off = [_parse_date(value, "additional_days_off entry") for value in raw_days_off]
    if len(days_off) != len(set(days_off)):
        raise ConfigurationError("additional_days_off must not contain duplicate dates")

    return TimetableConfig(
        timezone=timezone,
        installation_id=installation_id,
        weekly_timetable=weekly_timetable,
        subjects=subjects,
        additional_days_off=frozenset(days_off),
    )