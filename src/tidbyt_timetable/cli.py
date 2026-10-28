"""Command-line interface for preview, validation, and scheduled operations."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from tidbyt_timetable.calendar import CalendarCoverageError, SchoolCalendar
from tidbyt_timetable.config import ConfigurationError, WEEKDAYS, load_timetable
from tidbyt_timetable.renderer import render_timetable
from tidbyt_timetable.schedule import BERLIN, is_publish_time
from tidbyt_timetable.tidbyt_api import TidbytApiError, TidbytClient

ROOT = Path(__file__).resolve().parents[2]
TIMETABLE_PATH = ROOT / "config" / "timetable.yaml"
HOLIDAYS_PATH = ROOT / "config" / "holidays_ni.yaml"
ENV_PATH = ROOT / ".env"
WEEKDAY_NAMES = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def _read_local_credentials() -> tuple[str, str]:
    values = {key: os.environ[key] for key in ("TIDBYT_DEVICE_ID", "TIDBYT_API_TOKEN") if key in os.environ}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[7:].lstrip()
            key, separator, value = stripped.partition("=")
            if separator and key.strip() in ("TIDBYT_DEVICE_ID", "TIDBYT_API_TOKEN"):
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values.setdefault(key.strip(), value)

    device_id = values.get("TIDBYT_DEVICE_ID", "")
    api_token = values.get("TIDBYT_API_TOKEN", "")
    if not device_id.strip() or not api_token.strip():
        raise ValueError("Set TIDBYT_DEVICE_ID and TIDBYT_API_TOKEN in the environment or local .env file")
    return device_id, api_token


def _client() -> TidbytClient:
    return TidbytClient(*_read_local_credentials())


def _current_time() -> datetime:
    return datetime.now(BERLIN)


def _preview_date(value: str | None, weekday: str | None, timezone: ZoneInfo) -> date:
    if value:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("--date must use YYYY-MM-DD format") from error
        if parsed.isoformat() != value:
            raise ValueError("--date must use YYYY-MM-DD format")
        return parsed
    today = datetime.now(timezone).date()
    if weekday is None:
        return today
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(days=WEEKDAYS.index(weekday))


def _preview(day: date) -> int:
    timetable = load_timetable(TIMETABLE_PATH)
    image = render_timetable(timetable.lessons_for_date(day))
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    native_path = output_dir / "timetable.png"
    scaled_path = output_dir / "timetable-8x.png"
    image.save(native_path, format="PNG", optimize=False)
    image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST).save(
        scaled_path,
        format="PNG",
        optimize=False,
    )
    subjects = ", ".join(timetable.weekly_timetable[WEEKDAYS[day.weekday()]])
    print(
        f"Vorschau für {WEEKDAY_NAMES[day.weekday()]}, {day.isoformat()} "
        f"(reine Darstellung, keine Prüfung auf Schultag): {subjects}"
    )
    print(f"Native PNG: {native_path.relative_to(ROOT)}")
    print(f"8x-Vorschau: {scaled_path.relative_to(ROOT)}")
    return 0


def _validate_config() -> int:
    timetable = load_timetable(TIMETABLE_PATH)
    calendar = SchoolCalendar.from_file(HOLIDAYS_PATH, timetable.additional_days_off)
    print(
        f"Konfiguration gültig: fünf Stunden je Wochentag; "
        f"Ferienkalender {calendar.coverage_start} bis {calendar.coverage_end} "
        f"({len(calendar.ranges)} offizielle Zeiträume)."
    )
    return 0


def _publish() -> int:
    now = _current_time()
    if not is_publish_time(now):
        print(f"Keine Veröffentlichung: {now:%H:%M} Uhr liegt außerhalb des Fensters 06:30–08:00 Europe/Berlin.")
        return 0

    timetable = load_timetable(TIMETABLE_PATH)
    calendar = SchoolCalendar.from_file(HOLIDAYS_PATH, timetable.additional_days_off)
    if not calendar.is_school_day(now.date()):
        print(f"Keine Veröffentlichung: {now.date()} ist laut Schultagskalender kein Schultag.")
        return 0

    image = render_timetable(timetable.lessons_for_date(now.date()))
    _client().publish(image, timetable.installation_id)
    print(f"Stundenplan für {now.date()} im Hintergrund zur Tidbyt-Rotation hinzugefügt.")
    return 0


def _remove() -> int:
    timetable = load_timetable(TIMETABLE_PATH)
    removed = _client().remove(timetable.installation_id)
    if removed:
        print("Stundenplan-Installation entfernt.")
    else:
        print("Stundenplan-Installation war bereits entfernt (HTTP 404).")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tidbyt-timetable")
    commands = parser.add_subparsers(dest="command", required=True)

    preview_parser = commands.add_parser("preview", help="Erstellt eine rein lokale Bildvorschau")
    preview_source = preview_parser.add_mutually_exclusive_group()
    preview_source.add_argument("--date", help="Vorschautag im Format YYYY-MM-DD")
    preview_source.add_argument("--weekday", choices=WEEKDAYS, help="Wochentag für die Vorschau")

    commands.add_parser("publish", help="Geplanter Produktionsaufruf: Veröffentlichung nur im Zeitfenster")
    commands.add_parser("remove", help="Geplanter Produktionsaufruf: Stundenplan-Installation entfernen")
    commands.add_parser("validate-config", help="Prüft Stundenplan und offiziellen Ferienkalender")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preview":
            timetable = load_timetable(TIMETABLE_PATH)
            return _preview(_preview_date(args.date, args.weekday, timetable.timezone))
        if args.command == "validate-config":
            return _validate_config()
        if args.command == "publish":
            return _publish()
        if args.command == "remove":
            return _remove()
    except (CalendarCoverageError, ConfigurationError, TidbytApiError, ValueError, OSError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())