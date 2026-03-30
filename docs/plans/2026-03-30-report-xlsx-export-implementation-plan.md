# Report XLSX Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `.xlsx` versions of the user-facing attendance report tables in `out/<run_date>/` while keeping all existing CSV outputs unchanged.

**Architecture:** Extend `reporting.py` so each outgoing report table is defined once as headers plus rows, then written to both CSV and XLSX. Keep `summary.json`, `report.md`, and all `data/...` CSV files unchanged. Use a localized Ukrainian filename and headers only for the 10-day-period Excel artifact.

**Tech Stack:** Python 3.9, stdlib `csv/json/pathlib`, `openpyxl`, `unittest`.

---

### Task 1: Add XLSX dependency and table-writing primitives

**Files:**
- Modify: `requirements.txt`
- Modify: `src/school_attendance/reporting.py`
- Test: `tests/test_parser.py`

**Step 1: Write the failing test**

Add a focused test that imports `write_report_bundle(...)`, runs it in a temp directory, and asserts:

- `detail.xlsx` exists
- `student-absence-summary.xlsx` exists
- `відсутність-сьогодні-вчора.xlsx` exists
- workbook headers for one simple file match the CSV headers

Example assertion shape:

```python
from openpyxl import load_workbook

workbook = load_workbook(out_dir / "detail.xlsx")
sheet = workbook.active
headers = [cell.value for cell in sheet[1]]
self.assertEqual(
    ["student_id", "student_name", "class", "date", "lesson_no", "status", "reason_code"],
    headers,
)
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser.TestParserAndReporting.test_write_report_bundle_creates_xlsx_output_files -v
```

Expected: FAIL because `.xlsx` files are not created and/or `openpyxl` import is missing.

**Step 3: Write minimal implementation**

In `src/school_attendance/reporting.py`:

- add `openpyxl` import(s)
- add a helper like `_write_xlsx_table(path, headers, rows, sheet_title)`
- add small table-builder helpers where useful so CSV/XLSX share one data source
- generate `.xlsx` files for:
  - `detail`
  - `student-absence-summary`
  - `відсутність-сьогодні-вчора`

In `requirements.txt`:

- add `openpyxl` with a compatible version pin/range

**Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser.TestParserAndReporting.test_write_report_bundle_creates_xlsx_output_files -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add requirements.txt src/school_attendance/reporting.py tests/test_parser.py
git commit -m "feat: add xlsx exports for attendance reports"
```

### Task 2: Add localized ten-day-period Excel artifact

**Files:**
- Modify: `src/school_attendance/reporting.py`
- Test: `tests/test_parser.py`

**Step 1: Write the failing test**

Add tests covering both branches:

```python
def test_write_report_bundle_writes_localized_ten_day_periods_xlsx(self):
    # arrange ten_day_periods
    # assert file name is "періоди-відсутності-10-днів.xlsx"
    # assert worksheet headers are:
    # ["ID учня", "Учень", "Клас", "Період від", "Період до", "К-сть навчальних днів"]
```

```python
def test_write_report_bundle_skips_localized_ten_day_periods_xlsx_when_absent(self):
    # arrange no ten_day_periods
    # assert xlsx path key is absent
    # assert file does not exist
```

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_parser.TestParserAndReporting.test_write_report_bundle_writes_localized_ten_day_periods_xlsx \
  tests.test_parser.TestParserAndReporting.test_write_report_bundle_skips_localized_ten_day_periods_xlsx_when_absent -v
```

Expected: FAIL

**Step 3: Write minimal implementation**

In `src/school_attendance/reporting.py`:

- create localized XLSX path: `періоди-відсутності-10-днів.xlsx`
- keep CSV path/name unchanged: `ten-day-absence-periods.csv`
- add a dedicated header mapping for the Excel version:

```python
[
    "ID учня",
    "Учень",
    "Клас",
    "Період від",
    "Період до",
    "К-сть навчальних днів",
]
```

- write the Excel file only when `ten_day_periods_list` is non-empty
- add `ten_day_absence_periods_xlsx` to returned paths only when file exists

**Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_parser.TestParserAndReporting.test_write_report_bundle_writes_localized_ten_day_periods_xlsx \
  tests.test_parser.TestParserAndReporting.test_write_report_bundle_skips_localized_ten_day_periods_xlsx_when_absent -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/reporting.py tests/test_parser.py
git commit -m "feat: add localized ten-day absence xlsx export"
```

### Task 3: Cover pipeline-level output paths

**Files:**
- Modify: `tests/test_pipeline_dry_run.py`
- Optionally Modify: `src/school_attendance/reporting.py`

**Step 1: Write the failing test**

Add/extend a dry-run test so that after `run_daily(...)` it asserts:

- `result["paths"]["detail_xlsx"]` exists
- `result["paths"]["student_absence_summary_xlsx"]` exists
- `result["paths"]["class_absence_today_yesterday_xlsx"]` exists

Add a separate ten-day dry-run assertion for:

- `result["paths"]["ten_day_absence_periods_xlsx"]` exists when 10+ periods exist

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run -v
```

Expected: FAIL because the new path keys are not returned yet.

**Step 3: Write minimal implementation**

If needed, adjust `write_report_bundle(...)` return payload so `pipeline.run_daily(...)` exposes the new XLSX artifact paths without changing any existing keys.

**Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_pipeline_dry_run.py src/school_attendance/reporting.py
git commit -m "test: cover xlsx attendance artifacts in pipeline output"
```

### Task 4: Full regression verification

**Files:**
- Verify: `tests/test_parser.py`
- Verify: `tests/test_pipeline_dry_run.py`
- Verify: `tests/`

**Step 1: Run focused report tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_parser tests.test_pipeline_dry_run -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: PASS

**Step 3: Manual artifact sanity check**

Run one dry-run sample and verify in `out/<date>/`:

- CSV files still exist with the same names as before
- `detail.xlsx` exists
- `student-absence-summary.xlsx` exists
- `відсутність-сьогодні-вчора.xlsx` exists
- `періоди-відсутності-10-днів.xlsx` exists only when 10+ periods exist

**Step 4: Commit final polish (if any)**

```bash
git add requirements.txt src/school_attendance/reporting.py tests/test_parser.py tests/test_pipeline_dry_run.py
git commit -m "feat: export attendance reports to xlsx"
```
