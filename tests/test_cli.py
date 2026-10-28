from datetime import datetime
from zoneinfo import ZoneInfo

from tidbyt_timetable import cli


def test_preview_is_local_and_writes_native_and_scaled_images(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "TIMETABLE_PATH", cli.ROOT / "config" / "timetable.yaml")
    monkeypatch.setattr(cli, "HOLIDAYS_PATH", cli.ROOT / "config" / "holidays_ni.yaml")
    monkeypatch.setattr(cli, "ENV_PATH", tmp_path / ".env")
    (tmp_path / "config").mkdir()
    source = cli.Path(__file__).parents[1] / "config" / "timetable.yaml"
    (tmp_path / "config" / "timetable.yaml").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    assert cli.main(["preview", "--date", "2026-11-03"]) == 0
    assert (tmp_path / "output" / "timetable.png").exists()
    assert (tmp_path / "output" / "timetable-8x.png").exists()
    assert "reine Darstellung, keine Prüfung auf Schultag" in capsys.readouterr().out


def test_publish_outside_window_does_not_read_credentials_or_call_api(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_current_time", lambda: datetime(2026, 11, 3, 8, 7, tzinfo=ZoneInfo("Europe/Berlin")))
    monkeypatch.setattr(cli, "_client", lambda: (_ for _ in ()).throw(AssertionError("API client created")))

    assert cli.main(["publish"]) == 0
    assert "außerhalb des Fensters" in capsys.readouterr().out


def test_validate_config_reports_coverage(capsys):
    assert cli.main(["validate-config"]) == 0
    output = capsys.readouterr().out
    assert "2024-06-24 bis 2030-08-31" in output
    assert "offizielle Zeiträume" in output