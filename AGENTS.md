# AGENTS.md — School Timetable for Tidbyt Gen 1

> Repository-wide instructions for GitHub Copilot Agent Mode in VS Code.
> Product specification approved 2026-10-28. Implement this application in this repository, not merely a prototype.

## 1. Goal

Build a small, production-ready Python application that displays **today's five school lessons** on a **Tidbyt Gen 1 (64 × 32 RGB pixels)** using its **original firmware**. The app must use the Tidbyt **REST API directly** and run automatically through **GitHub Actions** at no additional service cost (subject to GitHub free-tier usage).

- On school days, make the timetable part of the device's normal app rotation between **06:30 and 08:00**, Europe/Berlin.
- After 08:00, remove that installation; perform independent cleanup attempts at **08:10** and **08:20**.
- Do not publish on weekends, official Niedersachsen school holidays, Niedersachsen statutory holidays, or manually configured days off.
- Never pin the timetable and never interrupt the current app on screen.
- Support a **local preview** and explicit local-only force options for production publish/remove; do not add manual GitHub workflow dispatch controls.
- Prioritize clarity, small dependencies, deterministic behavior, and tests.

The application is intentionally simple: no server, web UI, database, Pixlet dependency, alternate firmware, or paid hosting.

## 2. Confirmed timetable

The weekly timetable is manually configured. Each of the five school days currently uses:

| Lesson | Subject | Display text | Status |
| --- | --- | --- | --- |
| 1 | Deutsch | Deutsch | Known |
| 2 | Sport | Sport | Known |
| 3 | Mathe | Mathe | Known |
| 4 | Englisch | Englisch | Known |
| 5 | not supplied yet | blank | Intentionally unknown |

- This pattern applies **Monday through Friday** for now, but every day must be separately editable in YAML.
- There are **exactly five lesson slots**, never six. Do not render a sixth row.
- **Each slot represents one lesson period.** Repeated subjects in consecutive slots are permitted (double lessons are not grouped).
- Unknown lessons are accepted and **drawn blank** (their row and lesson number still appear); do not block publishing.
- Do not conflate an unknown blank subject with a confirmed school-free day.

## 3. Visual specification: FINAL DESIGN

**Five identical full-width horizontal rows**, not a two-column grid and not a mixed layout. The user explicitly rejected those alternative arrangements.

- Image canvas: **64 × 32 pixels**, generated natively at this size.
- A **single static frame**; no animations, scrolling, flashing, or transition effects.
- **No header, date, clock, weekday name, or extra icon.** Use all available space for lessons.
- Lesson number `1`–`5` on the left; the full subject name from the selected weekday to its right. Never render abbreviations.
- Same row geometry, alignment, spacing, and typography across all five rows.
- Each row spans the display width.
- Lesson 5 shows only its number until configured.
- Dark charcoal overall background with **very subtle** row containers, separators, and muted accent colors. **Avoid vivid/neon colors or heavily colored backgrounds.** Prefer neutral or near-black row fills; convey the subject through a muted text accent or tiny accent indicator.
- Use each configured subject's muted YAML color for its full name; unknown lessons use neutral gray. Exact RGB values are adjustable through the theme; default to low-saturation colors.
- Optimize for legibility on the actual low-resolution LED display. Use a small **embedded 3×5 or other suitable bitmap pixel font** with sufficient contrast. Avoid anti-aliased desktop fonts and floating-point rescaling.
- Five rows must fit within 32 px: for example five 5-pixel-high glyph regions with consistent 1-pixel gaps (and appropriate edge margins); no overlaps or clipped glyphs.
- Keep the rendered image deterministic for the same input.
- Make local preview output include a **native 64×32 PNG** and an optional enlarged nearest-neighbor image for inspection. The upload asset must be a **static WebP of exactly 64×32**.

Conceptual layout only (not to scale):

```text
+--------------------------------+
| 1   Deutsch                    |
|--------------------------------|
| 2   Sport                      |
|--------------------------------|
| 3   Mathe                      |
|--------------------------------|
| 4   Englisch                   |
|--------------------------------|
| 5                              |
+--------------------------------+
```

The reference design is deliberately understated. Do **not** create five broad saturated colored stripes.

## 4. Timing and behavior

Use `zoneinfo.ZoneInfo("Europe/Berlin")` for every calendar and time comparison; never use the runner's assumed local timezone.

| Schedule, Europe/Berlin | Task | Behavior |
| --- | --- | --- |
| 06:30 Monday–Friday | `publish` | Publish **only** if this is a school day **and** execution starts during `[06:30, 08:00)` |
| 08:00 daily | `remove` | Delete the installation, including on holidays/weekends to clean up stale content |
| 08:10 daily | `remove` | Independent cleanup attempt |
| 08:20 daily | `remove` | Independent final cleanup attempt |

**Idempotency and guards:**

1. Publishing always checks current **local date AND current time** before rendering/sending. It must never publish at or after 08:00, even when GitHub Actions runs late.
2. Publishing checks that today is a valid school day before sending.
3. Publishing uses the same fixed, alphanumeric installation ID (`schooltimetable`) every day, so a repeated publish updates an existing entry rather than creating duplicates.
4. Removal is allowed regardless of school-day status. Treat a documented `404 Not Found` for an already-absent installation as a successful no-op; do not swallow other failures.
5. The cleanup processes are independent GitHub Actions runs, **not in-process retries**.
6. **One outbound Tidbyt API request maximum per scheduled execution**, excluding zero-request no-op executions. No automatic HTTP retry adapter, loop, or exponential backoff.
7. HTTP errors, authentication errors, timeouts, bad configuration, or missing secrets should fail the GitHub Actions run with useful non-secret log messages.
8. GitHub Actions schedules are best effort; occasional missed or delayed appearances are acceptable, and removal may be late. Document that this cannot provide a hard 08:00 cutoff.
9. Apply GitHub workflow `concurrency` to avoid overlapping jobs operating on the same installation; disable cancel-in-progress. Runtime guards remain authoritative if jobs start out of order.
10. No UI setting should pin the custom installation; use background publication to join rotation quietly.

## 5. School-day calendar requirements

A date is a school day iff:

```text
Monday–Friday
AND not inside an official Niedersachsen school holiday interval
AND not a statutory public holiday in Niedersachsen
AND not present in manually configured additional days off
```

- Maintain an **offline, human-editable dataset** of Niedersachsen school holidays in YAML. Store ranges with inclusive start/end dates and a source URL or attribution.
- Seed the dataset from the **official Niedersachsen Ministry of Education holiday order** (not guessed dates or generic aggregators). The published holiday order currently covers school years 2024/25–2029/30; do **not** claim full coverage through 2030-12-31 unless that is actually supported. The official 2026 summer break is **2026-07-02 to 2026-08-12**.
- Include all officially announced non-contiguous single holidays (e.g. days after Ascension), not just the usual autumn/winter/spring/summer ranges.
- Calculate state statutory holidays via a maintained Python holiday library (e.g. `holidays.country_holidays("DE", subdiv="NI", years=...)`), or use an equivalent fully tested implementation. Keep this fully offline at runtime.
- Provide `additional_days_off` in YAML for school-specific non-teaching days.
- Perform coverage validation. If the official school calendar is incomplete for the requested production date, **fail closed** for publishing, emit a clear failure/warning, and do not mistakenly assume it is a school day. A scheduled deletion must still work even if the calendar configuration is incomplete.
- Validate inclusive bounds, date formats, and overlapping ranges. Overlap can be harmless but should be documented or warned about.
- No live third-party holiday API calls on school mornings.

Official source: https://www.mk.niedersachsen.de/service/ferientermine/schulferien-6491.html

## 6. Configuration

Use straightforward YAML, committed to git with no secrets. Suggested `config/timetable.yaml`:

```yaml
timezone: Europe/Berlin
installation_id: schooltimetable

weekly_timetable:
  monday:    ["Deutsch", "Sport", "Mathe", "Englisch", ""]
  tuesday:   ["Deutsch", "Sport", "Mathe", "Englisch", ""]
  wednesday: ["Deutsch", "Sport", "Mathe", "Englisch", ""]
  thursday:  ["Deutsch", "Sport", "Mathe", "Englisch", ""]
  friday:    ["Deutsch", "Sport", "Mathe", "Englisch", ""]

subjects:
  Deutsch:  {abbreviation: "DE", color: "#8CAAC4"}
  Sport:    {abbreviation: "SP", color: "#8DAE9B"}
  Mathe:    {abbreviation: "MA", color: "#C5AC81"}
  Englisch: {abbreviation: "EN", color: "#AAA0BE"}

additional_days_off: []
```

Colors are starting suggestions; choose readability on an LED matrix over strict matching. Put theme constants in code or a separate YAML file if it improves maintainability. Empty string `""` is a valid unknown subject, not a subject lookup failure. Exactly five items per weekday are required. Never silently truncate six items.

Suggested `config/holidays_ni.yaml`:

```yaml
source: https://www.mk.niedersachsen.de/service/ferientermine/schulferien-6491.html
coverage_start: "2026-01-01"
coverage_end: "2030-08-31" # EXAMPLE ONLY; replace with actual verified date coverage
ranges:
  - name: Sommerferien 2026
    start: "2026-07-02"
    end: "2026-08-12"
  - name: Herbstferien 2026
    start: "2026-10-12"
    end: "2026-10-24"
  # Agent: complete EVERY published holiday period and single day
```

**Important:** The above school-holiday fragment is **not a complete calendar**. Completing and validating the official calendar is an implementation task, and publishing must not be enabled with an incomplete placeholder dataset. Choose conservative accurate coverage and document the last covered date.

Secrets (GitHub Actions repository secrets, also local environment when needed):

```text
TIDBYT_DEVICE_ID
TIDBYT_API_TOKEN
```

Never commit credentials, print them, or place them in URLs. Add `.env`, `.venv/`, and `output/` to `.gitignore`.

## 7. Tidbyt REST API integration

Use only stock Tidbyt endpoints; **no Pixlet login**, Pixlet runtime, alternate firmware, or Tronbyt server.

### 7.1 Publish

```text
POST https://api.tidbyt.com/v0/devices/{device_id}/push
Authorization: Bearer {TIDBYT_API_TOKEN}
Content-Type: application/json
```

The request body must include these exact JSON fields:

```json
{
  "deviceID": "<device-id>",
  "image": "<base64-encoded-64x32-static-webp>",
  "installationID": "schooltimetable",
  "background": true
}
```

- `background: true` is essential: do not immediately replace the app currently visible.
- `installationID` ensures the image becomes part of normal rotation instead of a one-time foreground preview.
- Convert native 64×32 bitmap into a **static WebP** before base64 encoding. Check the result is valid and dimensions match.
- Do not confuse the REST API's `installationID` JSON key with `installation_id` or `installationId`.

### 7.2 Removal

```text
DELETE https://api.tidbyt.com/v0/devices/{device_id}/installations/{installation_id}
Authorization: Bearer {TIDBYT_API_TOKEN}
```

- URL-encode the installation ID as a path segment.
- Accept documented success codes (Pixlet's reference client expects HTTP 200); treat HTTP 404 as no-op success for a missing installation, and reject other errors.
- One request per execution, no retries.

### 7.3 Implementation references

Primary reference is the official Pixlet command source **only to confirm HTTP protocol**, not as a runtime dependency:
- https://github.com/tidbyt/pixlet/blob/v0.34.0/cmd/push.go
- https://github.com/tidbyt/pixlet/blob/v0.34.0/cmd/delete.go
- https://tidbyt.dev/docs/integrate/pushing-apps

These document the REST URLs, bearer authentication, base64 WebP body, stable installation ID, and background flag. This app should implement equivalent requests directly with `requests`.

## 8. GitHub Actions

- Use one compact workflow (preferred) in `.github/workflows/school-timetable.yml`, or separate schedules only if justified.
- Scheduled workflow must use **IANA timezone scheduling** (supported by GitHub Actions since March 2026) rather than manually hardcoding summer/winter UTC offsets:

```yaml
on:
  schedule:
    - cron: '30 6 * * 1-5'
      timezone: 'Europe/Berlin'
    - cron: '0 8 * * *'
      timezone: 'Europe/Berlin'
    - cron: '10 8 * * *'
      timezone: 'Europe/Berlin'
    - cron: '20 8 * * *'
      timezone: 'Europe/Berlin'
```

- If one workflow handles all four cron triggers, use `github.event.schedule` to map the event to `publish` or `remove` **and still validate actual local clock before publishing**.
- Run scheduled jobs from the repository's default branch.
- Checkout repository; set up a supported Python version (3.12+); install pinned, reproducible dependencies; run entrypoint.
- Minimal permissions: `contents: read`.
- Use secrets `TIDBYT_DEVICE_ID` and `TIDBYT_API_TOKEN` via environment variables.
- Use clear logs without credential exposure.
- Failing API operations result in a nonzero process exit; rely on standard GitHub Actions failure notifications (which depend on user's GitHub notification preferences).
- Do not add `workflow_dispatch` commands allowing ad hoc live publication/removal. The explicit `--force` CLI options are local-only; scheduled production runs never pass them.
- Document possibility of delayed or skipped GitHub scheduled runs, especially near the top of an hour.

GitHub docs: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule

## 9. Suggested repository structure

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .gitignore
├── config/
│   ├── timetable.yaml
│   └── holidays_ni.yaml
├── src/tidbyt_timetable/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── calendar.py
│   ├── schedule.py
│   ├── renderer.py
│   └── tidbyt_api.py
├── tests/
│   ├── test_config.py
│   ├── test_calendar.py
│   ├── test_schedule.py
│   ├── test_renderer.py
│   └── test_tidbyt_api.py
└── .github/workflows/
    ├── school-timetable.yml
    └── ci.yml
```

Dependencies should be limited to `Pillow`, `PyYAML`, `requests`, `holidays` and `pytest` (+ test mocking if necessary). Use Python stdlib for times, paths and CLI (`argparse`); avoid new frameworks.

### Local CLI contract

Implement these entry points:

```bash
python -m tidbyt_timetable.cli preview --date 2026-11-03
python -m tidbyt_timetable.cli preview --weekday monday
python -m tidbyt_timetable.cli publish
python -m tidbyt_timetable.cli remove
python -m tidbyt_timetable.cli validate-config
```

- `preview` does **not** require a Tidbyt token or network access and writes images to `output/`.
- Preview accepts an explicit date or weekday for design work even if that date would be a holiday; it is a **render-only preview**. It should clearly state what data is shown.
- `publish` and `remove` are production entrypoints. Their `--force` options are for explicit local operations only and must be rejected in GitHub Actions. Scheduled workflows must keep the time and school-day guard active by never passing `--force`.
- `publish` validates school-day and time rules before reading credentials/sending data.
- `validate-config` validates the weekly timetable and the official school calendar's coverage and records.

## 10. Implementation plan for Copilot

Implement in phases, delivering working tested code at each phase:

1. **Project skeleton:** packaging, dependencies, README, `.gitignore`.
2. **Config and calendar:** parse YAML and validate exactly five lessons/day; seed accurate official Niedersachsen holiday intervals through last covered date; calculate state public holidays; add manually configured days off.
3. **Renderer:** native pixel rendering with muted palette, no header, exactly five full-width rows; preview native PNG and nearest-neighbor magnified PNG; static WebP serialization; screenshots only if useful.
4. **Schedule engine:** clock-injected pure functions, school-day determination, publish guard, removal semantics.
5. **REST client:** bearer-auth JSON publish and DELETE; single attempt, timeout, error reporting, 404 idempotent removal.
6. **Production CLI:** `publish`, `remove`, `preview`, `validate-config`, documented exit codes.
7. **GitHub Actions:** timezone-aware scheduled actions, secrets, minimal privileges, non-overlap, CI tests.
8. **Docs/QA:** README explains local setup on macOS, how to edit lesson 5, how to maintain holiday dates and add extra days off, and limitations of best-effort scheduling.

Do not stop after scaffolding; complete implementation and automated tests. Do not ask the user for the unknown fifth lesson; use a blank entry as specified.

## 11. Required automated tests

**Calendar**
- Monday–Friday vs. weekends.
- Niedersachsen holiday **start, middle, and end dates** (inclusive).
- Example 2026 summer break: 2026-07-02 and 2026-08-12 are excluded.
- Niedersachsen public holidays, including regional ones.
- `additional_days_off` exclusion.
- Outside holiday dataset coverage: refuse to publish rather than assume school is in session.

**Timetable/config**
- Exactly five entries on every weekday, never six.
- Blank fifth lesson is valid and displayed as blank.
- Repeated subjects and individually editable weekday schedules.
- Invalid subject, invalid color, malformed date, missing weekday, missing coverage: useful errors.

**Renderer**
- Native output is 64×32; WebP decodes at 64×32 and is static.
- Exactly five consistent horizontal rows.
- No sixth row, no header, no scroll, no animation.
- Four known subject codes appear in expected positions; fifth has a number but no subject text.
- Palette stays muted; not five saturated stripes.
- Deterministic output bytes or stable pixel arrays for same config and day.

**Time/scheduling** (inject a test clock)
- Before 06:30: no publish.
- 06:30: publish allowed on a valid school day.
- 07:59: publish allowed.
- 08:00 and later: publish forbidden.
- Delayed publish event executed at 08:07 does nothing.
- European DST transitions are handled via `Europe/Berlin`.
- Removal on weekends/holidays still works.
- Repeated removal and 404 are successful no-ops.

**HTTP** (mock responses, never send real API requests in CI)
- Verify exact URL, method, bearer auth, `installationID` and `background: true`.
- Image is base64 WebP with correct dimensions.
- Publish and remove each send at most one request per run.
- 401, 403, 429, 500, timeouts produce a failed operation, not silent success.
- API token never appears in logs or errors.

## 12. Definition of done / acceptance criteria

The work is done when:

- [ ] A clean checkout installs and passes all tests.
- [ ] A local `preview` command produces a legible native 64×32 image and scaled preview showing **five full-width rows**.
- [ ] Rows show the full configured subject names; an unknown blank slot displays only its lesson number.
- [ ] All weekday schedules are editable in YAML and validated as exactly five lessons.
- [ ] Niedersachsen holidays (from official source), state public holidays, weekends and manual days off are excluded.
- [ ] Publishing happens only in `[06:30,08:00)` Berlin time on valid school days.
- [ ] Normal Tidbyt app rotation is preserved using a stable installation and background push.
- [ ] Production removes installation at 08:00, plus independent cleanup at 08:10/08:20.
- [ ] Delete of a missing installation is treated as success; other API failures fail the workflow.
- [ ] No API retries within an execution; no manual GitHub workflow dispatch; local force flags remain explicit and guarded.
- [ ] Secrets are injected using GitHub Actions, never stored in source.
- [ ] The README covers first-time setup, GitHub secrets, local preview, timetable changes, holiday data maintenance, limitations, and troubleshooting.

## 13. Agent behavior and safety

- Implement according to confirmed decisions; **do not redesign the UI** into columns or add a header.
- Prefer small, testable pure functions and straightforward, typed Python.
- Keep one stable installation ID; do not modify/delete other apps on the user's Tidbyt.
- No production API calls in tests or during local preview.
- Do not fabricate unsupported holiday dates or API features. Prefer authoritative sources and note any integration uncertainty in the README.
- If possible, verify actual API behavior only after the user chooses to deploy to their device; there are no credentials available in this spec.
- Keep the initial scope narrow. Future extensions (date overrides, multiple children, automatic holiday updates) must not be added unless requested.

### Recommended Copilot Agent Mode task

> Read `AGENTS.md` and implement this repository end to end. Work in the specified phases, create the Python package, configuration, local pixel renderer, official school-day detection, Tidbyt REST client, GitHub Actions workflows, tests, and README. Do not use Pixlet or change firmware. Run tests and generate a local preview before considering implementation complete. Do not publish anything to a physical Tidbyt during development.
