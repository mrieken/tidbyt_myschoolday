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


def test_force_publish_bypasses_time_and_calendar_guards(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(cli, "_current_time", lambda: datetime(2026, 11, 3, 15, 19, tzinfo=ZoneInfo("Europe/Berlin")))
    monkeypatch.setattr(
        cli.SchoolCalendar,
        "from_file",
        lambda *args: (_ for _ in ()).throw(AssertionError("calendar guard must be skipped")),
    )
    published = []

    class Client:
        def publish(self, image, installation_id):
            published.append(installation_id)

    monkeypatch.setattr(cli, "_client", Client)

    assert cli.main(["publish", "--force"]) == 0
    assert published == ["schooltimetable"]
    assert "FORCE" in capsys.readouterr().out


def test_force_is_rejected_inside_github_actions(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(cli, "_client", lambda: (_ for _ in ()).throw(AssertionError("API client created")))

    assert cli.main(["publish", "--force"]) == 1
    assert "only available for local CLI use" in capsys.readouterr().err


def test_force_publish_without_weekend_timetable_fails_without_api(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(cli, "_current_time", lambda: datetime(2026, 10, 31, 15, 19, tzinfo=ZoneInfo("Europe/Berlin")))
    monkeypatch.setattr(cli, "_client", lambda: (_ for _ in ()).throw(AssertionError("API client created")))

    assert cli.main(["publish", "--force"]) == 1
    assert "No Saturday or Sunday timetable" in capsys.readouterr().err


def test_force_remove_is_available_locally(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    removed = []

    class Client:
        def remove(self, installation_id):
            removed.append(installation_id)
            return True

    monkeypatch.setattr(cli, "_client", Client)

    assert cli.main(["remove", "--force"]) == 0
    assert removed == ["schooltimetable"]
    assert "FORCE" in capsys.readouterr().out


def test_validate_config_reports_coverage(capsys):
    assert cli.main(["validate-config"]) == 0
    output = capsys.readouterr().out
    assert "2024-06-24 bis 2030-08-31" in output
    assert "offizielle Zeiträume" in output