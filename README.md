# Tidbyt School Timetable

Displays five configured school lessons on a Tidbyt Gen 1 during the morning app rotation. The renderer creates native 64×32 pixel art; the production client uses the Tidbyt REST API directly, with no Pixlet runtime, additional server, or live holiday lookup.

## Local Setup

Requires Python 3.12 or newer. From the repository directory on macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

Create a local preview without credentials or network access:

```sh
python -m tidbyt_timetable.cli preview --date 2026-11-03
python -m tidbyt_timetable.cli preview --weekday monday
```

The commands write `output/timetable.png` (64×32) and `output/timetable-8x.png` (nearest-neighbor enlargement). Preview is render-only and does not decide whether the selected date is a school day.

Run checks with:

```sh
python -m pytest
python -m tidbyt_timetable.cli validate-config
```

## Timetable Changes

Edit `config/timetable.yaml`. Each weekday is configured independently and must contain exactly five entries. An empty string is an intentionally unknown lesson; it keeps the numbered row blank. The renderer displays each subject's full name, not its optional abbreviation, using the embedded 3×5 pixel font. Names must use supported display characters and fit within 12 characters. Each subject must have a muted `#RRGGBB` color. Consecutive repeated subjects are kept as separate periods.

## Holiday Calendar

`config/holidays_ni.yaml` is an offline transcription of the Niedersachsen Ministry of Education's [official holiday order](https://www.mk.niedersachsen.de/service/ferientermine/schulferien-6491.html), including the individual non-contiguous days. Its declared coverage is 2024-06-24 through 2030-08-31; dates outside that range fail closed for publication. The 2030 summer dates are included as published in the order; no coverage is claimed through 2030-12-31. Niedersachsen statutory public holidays are calculated offline with the `holidays` package. Add school-specific non-teaching dates to `additional_days_off` in `config/timetable.yaml`.

Ranges use inclusive bounds. Overlapping ranges are accepted with a warning. Verify every change against the official source, then run `validate-config` and the calendar tests.

## Scheduled Operation

Add the GitHub repository secrets `TIDBYT_DEVICE_ID` and `TIDBYT_API_TOKEN`. The scheduled workflow uses Berlin local-time schedules: weekdays at 06:30 publish in the background under the stable, alphanumeric `schooltimetable` installation ID; every day at 08:00, 08:10, and 08:20 performs an independent removal attempt. It never pins the app or interrupts the app currently on screen. A missing installation (HTTP 404) is a successful no-op.

For local production operations only, the CLI reads the same two variables from the process environment or a root `.env` file. Keep `.env` private; it is ignored by git. `preview` and `validate-config` never read credentials. A local `publish --force` skips both time-window and school-day checks; `remove --force` explicitly requests removal. These force options are rejected inside GitHub Actions and are not used by the scheduled workflow. Both commands make live API requests when successful, so use them deliberately.

```sh
./.venv/bin/python -m tidbyt_timetable.cli publish --force
./.venv/bin/python -m tidbyt_timetable.cli remove --force
```

Forced publication still requires a weekday timetable; no weekend timetable is configured.

GitHub Actions schedules are best effort and may be delayed or skipped, particularly near the top of an hour. Runtime checks prevent a delayed publish at or after 08:00, but scheduled cleanup cannot guarantee removal exactly at 08:00. Concurrency prevents overlapping workflow runs; each execution makes at most one API request and does not retry it.

## Troubleshooting

- `validate-config` reports unknown subjects, malformed dates, missing weekdays, or lesson counts that differ from five: correct the YAML and rerun validation.
- A publish run outside 06:30–08:00 Berlin time or on a non-school day exits successfully without reading credentials or contacting Tidbyt.
- A publish date outside holiday-calendar coverage fails closed. Extend coverage only after checking an official Niedersachsen publication.
- HTTP errors and timeouts fail the operation with a status-only message; credentials and response bodies are not printed.