# Attendance 10+ Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated `run-attendance-10plus` command that collects data from `Журнали -> Відвідуваність` and writes only the 10+ consecutive-absence report in Ukrainian CSV/XLSX formats.

**Architecture:** Keep the new flow isolated from `run-daily`: a separate collector entrypoint gathers attendance-overview rows by class, adapts them into `AttendanceRecord`, reuses existing 10-day analytics, and writes a dedicated attendance-only report bundle. Existing daily reporting remains unchanged.

**Tech Stack:** Python 3.9, Playwright sync API, stdlib `csv/json/pathlib`, existing custom XLSX writer, `unittest`.

---

### Task 1: Add CLI entrypoint for the new command

**Files:**
- Modify: `src/school_attendance/cli.py`
- Test: `tests/test_cli_run_daily_command.py`
- Create: `tests/test_cli_run_attendance_10plus_command.py`

**Step 1: Write the failing test**

```python
@patch("builtins.print")
@patch("school_attendance.cli.run_attendance_10plus")
@patch("school_attendance.cli.load_config")
def test_run_attendance_10plus_dispatches_handler(...):
    code = cli.main(
        [
            "run-attendance-10plus",
            "--run-date", "2026-03-30",
            "--class", "10-А",
            "--class", "8-Б",
        ]
    )

    self.assertEqual(0, code)
    kwargs = mock_run_attendance_10plus.call_args.kwargs
    self.assertEqual(["10-А", "8-Б"], kwargs["include_classes"])
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli_run_attendance_10plus_command -v
```

Expected: FAIL because the command and handler do not exist.

**Step 3: Write minimal implementation**

In `src/school_attendance/cli.py`:
- add new subparser `run-attendance-10plus`
- mirror the useful flags from `run-daily`
- import and call new pipeline function `run_attendance_10plus(...)`

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli_run_attendance_10plus_command -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/cli.py tests/test_cli_run_attendance_10plus_command.py
git commit -m "feat: add attendance 10plus cli command"
```

### Task 2: Add attendance-only reporting writer and dry-run pipeline

**Files:**
- Modify: `src/school_attendance/pipeline.py`
- Modify: `src/school_attendance/reporting.py`
- Test: `tests/test_parser.py`
- Test: `tests/test_pipeline_dry_run.py`

**Step 1: Write the failing tests**

```python
def test_write_attendance_10plus_report_bundle_writes_ukrainian_csv_and_xlsx(self):
    period_rows = [
        {
            "student_id": "123",
            "student_name": "Іваненко Іван",
            "class_name": "7-А",
            "period_start": "2026-02-01",
            "period_end": "2026-02-14",
            "learning_days_absent": 10,
        }
    ]

    paths = write_attendance_10plus_report_bundle(...)
    self.assertTrue((out_dir / "періоди-відсутності-10-днів-відвідуваність.csv").exists())
    self.assertTrue((out_dir / "періоди-відсутності-10-днів-відвідуваність.xlsx").exists())
```

```python
def test_run_attendance_10plus_dry_run_writes_only_attendance_10plus_outputs(self):
    result = run_attendance_10plus(..., dry_run=True, skip_collect=True, raw_files=[raw_file])
    self.assertIn("attendance_10plus_csv", result["paths"])
    self.assertIn("attendance_10plus_xlsx", result["paths"])
    self.assertNotIn("report_md", result["paths"])
```

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_parser.TestParserAndReporting.test_write_attendance_10plus_report_bundle_writes_ukrainian_csv_and_xlsx \
  tests.test_pipeline_dry_run.TestPipelineDryRun.test_run_attendance_10plus_dry_run_writes_only_attendance_10plus_outputs -v
```

Expected: FAIL because the dedicated writer/pipeline do not exist.

**Step 3: Write minimal implementation**

In `src/school_attendance/reporting.py`:
- add `write_attendance_10plus_report_bundle(...)`
- write:
  - `періоди-відсутності-10-днів-відвідуваність.csv`
  - `періоди-відсутності-10-днів-відвідуваність.xlsx`

In `src/school_attendance/pipeline.py`:
- add `run_attendance_10plus(...)`
- for `dry_run/skip_collect`, read provided raw CSV files
- build `AttendanceRecord` rows
- run `build_ten_day_absence_periods(...)`
- write only the dedicated attendance-only outputs

**Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser tests.test_pipeline_dry_run -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/pipeline.py src/school_attendance/reporting.py tests/test_parser.py tests/test_pipeline_dry_run.py
git commit -m "feat: add attendance-only 10plus reporting pipeline"
```

### Task 3: Add collector helpers for the attendance overview page

**Files:**
- Modify: `src/school_attendance/collector.py`
- Modify: `config/nz_selectors.json`
- Test: `tests/test_collector_journal_records.py`

**Step 1: Write the failing tests**

Add focused helper-level tests such as:

```python
def test_extract_attendance_overview_class_options(self):
    # fake payload/dom with 0-А, 0-Б, 1-А
    # assert parsed class names list
```

```python
def test_normalize_attendance_overview_rows_to_records(self):
    # fake attendance overview rows by day
    # assert result rows have lesson_no=1 and correct ABSENT/PRESENT statuses
```

```python
def test_filter_attendance_overview_classes_by_include_tokens(self):
    # assert --class filter keeps only selected classes
```

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_collector_journal_records -v
```

Expected: FAIL because the helper functions do not exist.

**Step 3: Write minimal implementation**

In `src/school_attendance/collector.py`:
- add new public collector entrypoint:

```python
def collect_attendance_overview_exports(config, run_date, include_classes=None) -> List[Path]:
    ...
```

- add helpers to:
  - open `Журнали -> Відвідуваність`
  - enumerate class options
  - extract day-level student attendance from state payload first, DOM second
  - convert extracted rows into a raw CSV compatible with `parse_attendance_csv(...)`

In `config/nz_selectors.json`:
- add `attendance_overview` selectors block

**Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_collector_journal_records -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/collector.py config/nz_selectors.json tests/test_collector_journal_records.py
git commit -m "feat: collect attendance overview by class"
```

### Task 4: Wire live collection into the new command

**Files:**
- Modify: `src/school_attendance/pipeline.py`
- Modify: `src/school_attendance/collector.py`
- Test: `tests/test_pipeline_dry_run.py`

**Step 1: Write the failing test**

```python
@patch("school_attendance.pipeline.collect_attendance_overview_exports")
def test_run_attendance_10plus_passes_include_classes_to_overview_collection(...):
    run_attendance_10plus(..., include_classes=["10-А", "8-Б"])
    mock_collect.assert_called_once_with(config, run_date, include_classes=["10-А", "8-Б"])
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run.TestPipelineDryRun.test_run_attendance_10plus_passes_include_classes_to_overview_collection -v
```

Expected: FAIL because the new pipeline does not call the dedicated collector yet.

**Step 3: Write minimal implementation**

In `src/school_attendance/pipeline.py`:
- when not `dry_run` and not `skip_collect`, call `collect_attendance_overview_exports(...)`
- keep `run-daily` untouched

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run.TestPipelineDryRun.test_run_attendance_10plus_passes_include_classes_to_overview_collection -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/pipeline.py tests/test_pipeline_dry_run.py
git commit -m "feat: wire attendance overview collection into 10plus command"
```

### Task 5: Full regression verification

**Files:**
- Verify: `tests/`

**Step 1: Run focused suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_cli_run_attendance_10plus_command \
  tests.test_collector_journal_records \
  tests.test_parser \
  tests.test_pipeline_dry_run -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: PASS

**Step 3: Manual sanity check**

Run:

```bash
PYTHONPATH=src python3 -m school_attendance.cli run-attendance-10plus --run-date <date>
```

Expected:
- only attendance-only files are produced in `out/<date>/`
- each 10+ period is a separate row
- files use Ukrainian names and headers

**Step 4: Commit final polish**

```bash
git add src/school_attendance/cli.py src/school_attendance/pipeline.py src/school_attendance/collector.py src/school_attendance/reporting.py config/nz_selectors.json tests
git commit -m "feat: add attendance overview 10plus command"
```
