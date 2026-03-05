# Class Absence Today-Yesterday Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new CSV file with class-level absent-student counts for today and yesterday, and localize `student-absence-summary.csv` column headers to Ukrainian.

**Architecture:** Compute class-day aggregates in analytics (unique absent students by class for today/yesterday + class ordering), pass structured result via pipeline, and write output artifacts in reporting with localized headers.

**Tech Stack:** Python 3.9, stdlib `csv/datetime/re`, unittest.

---

### Task 1: Add class daily absence analytics

**Files:**
- Modify: `src/school_attendance/analytics.py`
- Test: `tests/test_kpi_metrics.py`

**Step 1: Write the failing test**

```python
def test_build_class_absence_today_yesterday_counts_and_sorting(self):
    # create mixed classes (11-А, 11-Б, 10-А)
    # verify unique absent student counting for run_date and run_date-1
    # verify order: 11-А, 11-Б, 10-А
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_kpi_metrics.TestKpiMetrics.test_build_class_absence_today_yesterday_counts_and_sorting -v`
Expected: FAIL due missing function.

**Step 3: Write minimal implementation**

```python
def build_class_absence_today_yesterday(records, run_date):
    # classes from today/yesterday rows
    # unique absent students per class/day
    # totals and sorted class rows
```

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/analytics.py tests/test_kpi_metrics.py
git commit -m "feat: add class daily absence analytics"
```

### Task 2: Wire analytics into pipeline and reporting output

**Files:**
- Modify: `src/school_attendance/pipeline.py`
- Modify: `src/school_attendance/reporting.py`
- Test: `tests/test_pipeline_dry_run.py`
- Test: `tests/test_parser.py`

**Step 1: Write failing tests**

```python
def test_run_daily_writes_ukrainian_class_daily_absence_csv(self):
    # run dry-run
    # assert paths contains class daily csv
    # assert first row is "усього"
```

```python
def test_student_absence_summary_headers_are_ukrainian(self):
    # run report bundle
    # assert csv headers in ukrainian
```

**Step 2: Run tests to verify they fail**

Run:
- `PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run.TestPipelineDryRun.test_run_daily_writes_ukrainian_class_daily_absence_csv -v`
- `PYTHONPATH=src python3 -m unittest tests.test_parser.TestParserAndReporting.test_student_absence_summary_headers_are_ukrainian -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pipeline.py
class_daily_absence = build_class_absence_today_yesterday(...)
write_report_bundle(..., class_daily_absence=class_daily_absence)

# reporting.py
_write_class_absence_today_yesterday_csv(path, class_daily_absence)
# rename student-absence-summary headers to ukrainian
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run tests.test_parser -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/pipeline.py src/school_attendance/reporting.py tests/test_pipeline_dry_run.py tests/test_parser.py
git commit -m "feat: add ukrainian class absence daily file and localized headers"
```

### Task 3: Full regression verification

**Files:**
- Verify: `tests/`

**Step 1: Run full suite**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 2: Validate artifact names and columns (dry-run)**

Run sample dry-run and verify:
- `відсутність-сьогодні-вчора.csv` exists
- first data row is `усього,...`
- `student-absence-summary.csv` headers are ukrainian

**Step 3: Commit docs (if updated)**

```bash
git add README.md docs/ops/attendance/start-guide.md
git commit -m "docs: update report artifacts with ukrainian class daily absence file"
```
