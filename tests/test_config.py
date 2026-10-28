from datetime import date
from pathlib import Path

import pytest

from tidbyt_timetable.config import ConfigurationError, load_timetable

CONFIG_PATH = Path(__file__).parents[1] / "config" / "timetable.yaml"


def test_config_has_five_editable_weekday_slots_and_subject_names():
    config = load_timetable(CONFIG_PATH)

    assert set(config.weekly_timetable) == {"monday", "tuesday", "wednesday", "thursday", "friday"}
    assert all(len(lessons) == 5 for lessons in config.weekly_timetable.values())
    assert config.lessons_for_date(date(2026, 10, 28))[0].name == "Deutsch"
    assert config.lessons_for_date(date(2026, 10, 28))[3].name == "Sachkunde"


def test_blank_unknown_lesson_remains_valid_and_has_no_subject_name(tmp_path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "monday: [Deutsch, Deutsch, Mathe, Englisch, Sport]",
        'monday: [Deutsch, Deutsch, Mathe, Englisch, ""]',
    )
    config_path = tmp_path / "timetable.yaml"
    config_path.write_text(text, encoding="utf-8")

    assert load_timetable(config_path).lessons_for_date(date(2026, 10, 26))[4].name == ""


def test_config_rejects_sixth_lesson(tmp_path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "friday: [Deutsch, Religion, Mathe, Kunst, Betreuung]",
        "friday: [Deutsch, Religion, Mathe, Kunst, Betreuung, Sport]",
    )
    config_path = tmp_path / "timetable.yaml"
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigurationError, match="exactly five"):
        load_timetable(config_path)


def test_config_rejects_unknown_subject_and_invalid_color(tmp_path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "tuesday: [Deutsch, Mathe, Musik, Sport, Kunst]",
        "tuesday: [Deutsch, Mathe, Unbekannt, Sport, Kunst]",
    )
    config_path = tmp_path / "timetable.yaml"
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigurationError, match="unknown subjects"):
        load_timetable(config_path)

    text = CONFIG_PATH.read_text(encoding="utf-8").replace("#8CAAC4", "blue")
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="#RRGGBB"):
        load_timetable(config_path)


def test_weekdays_are_individually_editable_and_repeated_subjects_are_valid(tmp_path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "tuesday: [Deutsch, Mathe, Musik, Sport, Kunst]",
        "tuesday: [Deutsch, Deutsch, Musik, Sport, Kunst]",
    )
    config_path = tmp_path / "timetable.yaml"
    config_path.write_text(text, encoding="utf-8")

    config = load_timetable(config_path)
    assert config.weekly_timetable["tuesday"][:2] == ("Deutsch", "Deutsch")
    assert config.weekly_timetable["wednesday"][1] == "Religion"


def test_config_rejects_missing_weekday_and_malformed_manual_date(tmp_path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "friday: [Deutsch, Religion, Mathe, Kunst, Betreuung]\n",
        "",
    )
    config_path = tmp_path / "timetable.yaml"
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="exactly monday"):
        load_timetable(config_path)

    text = CONFIG_PATH.read_text(encoding="utf-8").replace(
        "additional_days_off: []",
        'additional_days_off: ["2026-02-30"]',
    )
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="YYYY-MM-DD"):
        load_timetable(config_path)