# Ten-Day Absence Periods Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add semester-level 10+ learning-day absence periods to student summaries and generate optional detailed CSV output when such periods exist.

**Architecture:** Compute 10+ absence periods in analytics from normalized attendance rows grouped per student/day. Pass period aggregates through pipeline to reporting, where summary tables are extended and an additional CSV is written only when periods are present.

**Tech Stack:** Python 3, stdlib `datetime/csv`, unittest.

---

### Task 1: Add analytics for semester 10+ learning-day periods

**Files:**
- Modify: `src/school_attendance/analytics.py`
- Test: `tests/test_kpi_metrics.py`

**Step 1: Write the failing test**

```python
def test_build_ten_day_absence_periods_returns_multiple_periods(self):
    records = [
        # student 1: 10-day period + break + 11-day period
        # student 2: 9-day period (must be ignored)
    ]

    student_summary, periods = build_ten_day_absence_periods(
        records=records,
        semester_start=date(2026, 1, 12),
        run_date=date(2026, 3, 4),
        min_learning_days=10,
    )

    self.assertEqual(2, student_summary["s1"]["ten_plus_periods_count"])
    self.assertEqual("2026-02-10", student_summary["s1"]["last_period_end"])
    self.assertEqual(2, len([p for p in periods if p["student_id"] == "s1"]))
    self.assertNotIn("s2", student_summary)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_kpi_metrics.TestKpiMetrics.test_build_ten_day_absence_periods_returns_multiple_periods -v`
Expected: FAIL with import/name error because `build_ten_day_absence_periods` is missing.

**Step 3: Write minimal implementation**

```python
def build_ten_day_absence_periods(records, semester_start, run_date, min_learning_days=10):
    # 1) group rows by student->date
    # 2) mark date as absent-day if any row.status == "ABSENT"
    # 3) walk sorted learning days to build streaks
    # 4) keep streaks with len >= min_learning_days
    # 5) return (summary_by_student, period_rows)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests.test_kpi_metrics.TestKpiMetrics.test_build_ten_day_absence_periods_returns_multiple_periods -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_kpi_metrics.py src/school_attendance/analytics.py
git commit -m "feat: add analytics for 10-day absence periods"
```

### Task 2: Thread period analytics through pipeline and reporting outputs

**Files:**
- Modify: `src/school_attendance/pipeline.py`
- Modify: `src/school_attendance/reporting.py`
- Test: `tests/test_pipeline_dry_run.py`
- Test: `tests/test_parser.py`

**Step 1: Write the failing tests**

```python
def test_run_daily_writes_ten_day_periods_csv_when_present(self):
    # feed dry-run data with a 10+ period
    # assert paths include ten_day_absence_periods_csv
    # assert file exists and has expected row


def test_run_daily_skips_ten_day_periods_csv_when_absent(self):
    # feed data without 10+ period
    # assert path key absent and file missing
```

```python
def test_write_report_bundle_contains_new_ten_plus_columns(self):
    # assert student-absence-summary.csv includes new columns
    # assert report.md table includes new columns and values
```

**Step 2: Run tests to verify they fail**

Run:
- `PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run.TestPipelineDryRun.test_run_daily_writes_ten_day_periods_csv_when_present -v`
- `PYTHONPATH=src python3 -m unittest tests.test_parser.TestParserAndReporting.test_write_report_bundle_contains_new_ten_plus_columns -v`

Expected: FAIL because reporting/pipeline signatures and outputs do not include ten-day period data.

**Step 3: Write minimal implementation**

```python
# pipeline.py
summary_by_student, ten_day_periods = build_ten_day_absence_periods(...)
paths = write_report_bundle(..., ten_day_summary=summary_by_student, ten_day_periods=ten_day_periods)
if ten_day_periods:
    include ten_day_absence_periods_csv in return paths
```

```python
# reporting.py
# extend grouped rows with ten_plus_periods_count + last_ten_plus_period
# add markdown columns for those fields
# write ten-day-absence-periods.csv only if rows exist
```

**Step 4: Run tests to verify they pass**

Run:
- `PYTHONPATH=src python3 -m unittest tests.test_pipeline_dry_run tests.test_parser -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/school_attendance/pipeline.py src/school_attendance/reporting.py tests/test_pipeline_dry_run.py tests/test_parser.py
git commit -m "feat: expose 10-day absence periods in reports"
```

### Task 3: Full regression verification

**Files:**
- Verify: `tests/`

**Step 1: Run full suite**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS, no regressions.

**Step 2: Spot-check artifacts format (dry-run)**

Run: `PYTHONPATH=src python3 -m school_attendance.cli run-daily --dry-run --skip-collect --raw-file data/raw/<date>/attendance-journal.csv --run-date <date>`
Expected: `report.md` and `student-absence-summary.csv` include new columns; `ten-day-absence-periods.csv` appears only when periods exist.

**Step 3: Commit (if needed for docs/tests updates)**

```bash
git add docs/ops/attendance/start-guide.md README.md
git commit -m "docs: describe 10-day absence period outputs"
```
