# NZ Attendance App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Реалізувати Python CLI-додаток, який автоматизує збір даних з nz.ua та формує щоденні звіти відвідуваності за правилами школи.

**Architecture:** Додаток будується модульно: `collector` отримує raw-дані, `parser` нормалізує записи, `analytics` обчислює KPI та інциденти, `reporting` формує фінальні файли. Оркестрація виконується через CLI-команду `run-daily` з підтримкою `--dry-run` і `--skip-collect`.

**Tech Stack:** Python 3.9+, stdlib (`csv`, `json`, `argparse`, `datetime`, `dataclasses`, `unittest`), optional `playwright` для збору даних, optional PDF рендерер.

---

### Task 1: Scaffold проєкту та конфігурації

**Files:**
- Create: `src/school_attendance/__init__.py`
- Create: `src/school_attendance/config.py`
- Create: `src/school_attendance/models.py`
- Create: `src/school_attendance/cli.py`
- Create: `requirements.txt`
- Modify: `.gitignore`
- Create: `.env.example`

**Step 1: Додати failing smoke-test імпорту CLI**

```python
# tests/test_cli_smoke.py
import unittest

class TestCliSmoke(unittest.TestCase):
    def test_can_import_cli(self):
        from school_attendance import cli  # noqa: F401
```

**Step 2: Запустити test для RED**

Run: `PYTHONPATH=src python3 -m unittest tests/test_cli_smoke.py -v`
Expected: FAIL (module not found).

**Step 3: Додати мінімальний каркас модулів**

```python
# src/school_attendance/__init__.py
__all__ = []
```

**Step 4: Запустити test для GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests/test_cli_smoke.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/school_attendance tests/test_cli_smoke.py .gitignore .env.example requirements.txt
git commit -m "feat: scaffold attendance app package and config"
```

### Task 2: Реалізувати аналітику інцидентів "втік" (1+)

**Files:**
- Create: `tests/test_escape_incidents.py`
- Create: `src/school_attendance/analytics.py`

**Step 1: Написати failing тести для правила 1+ і винятків**

```python
def test_marks_incident_after_first_presence_with_unexcused_absence():
    ...
```

**Step 2: Запустити RED**

Run: `PYTHONPATH=src python3 -m unittest tests/test_escape_incidents.py -v`
Expected: FAIL (missing implementation).

**Step 3: Реалізувати мінімальну логіку `detect_escape_incidents`**

```python
def detect_escape_incidents(records, excused_codes):
    ...
```

**Step 4: Запустити GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests/test_escape_incidents.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_escape_incidents.py src/school_attendance/analytics.py
git commit -m "feat: implement escape incident detection rule"
```

### Task 3: KPI-обчислення періодів 7/30/семестр

**Files:**
- Create: `tests/test_kpi_metrics.py`
- Modify: `src/school_attendance/analytics.py`

**Step 1: Написати failing тести KPI**

```python
def test_period_metrics_7_days():
    ...
```

**Step 2: Запустити RED**

Run: `PYTHONPATH=src python3 -m unittest tests/test_kpi_metrics.py -v`
Expected: FAIL.

**Step 3: Реалізувати `build_period_summary` та `build_student_risk_list`**

```python
def build_period_summary(...):
    ...
```

**Step 4: Запустити GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests/test_kpi_metrics.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_kpi_metrics.py src/school_attendance/analytics.py
git commit -m "feat: add kpi analytics for 7/30/semester windows"
```

### Task 4: Parser і Reporting

**Files:**
- Create: `tests/test_parser.py`
- Create: `src/school_attendance/parser.py`
- Create: `src/school_attendance/reporting.py`

**Step 1: Написати failing parser test на CSV шаблон**

```python
def test_parse_attendance_csv_template_columns():
    ...
```

**Step 2: Запустити RED**

Run: `PYTHONPATH=src python3 -m unittest tests/test_parser.py -v`
Expected: FAIL.

**Step 3: Реалізувати parser + writer для `summary.json`, `detail.csv`, `report.md`**

```python
def parse_attendance_csv(path):
    ...
```

**Step 4: Запустити GREEN**

Run: `PYTHONPATH=src python3 -m unittest tests/test_parser.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_parser.py src/school_attendance/parser.py src/school_attendance/reporting.py
git commit -m "feat: add csv parser and report writers"
```

### Task 5: Collector (RPA) + Pipeline + CLI

**Files:**
- Create: `src/school_attendance/collector.py`
- Create: `src/school_attendance/pipeline.py`
- Modify: `src/school_attendance/cli.py`
- Modify: `README.md`
- Modify: `docs/ops/attendance/start-guide.md`

**Step 1: Написати failing test pipeline у dry-run режимі**

```python
def test_run_daily_dry_run_from_local_csv():
    ...
```

**Step 2: Запустити RED**

Run: `PYTHONPATH=src python3 -m unittest tests/test_pipeline_dry_run.py -v`
Expected: FAIL.

**Step 3: Реалізувати pipeline та CLI (`run-daily`, `--dry-run`, `--skip-collect`)**

```python
def run_daily(config, run_date, ...):
    ...
```

**Step 4: Запустити GREEN + повний набір тестів**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/school_attendance README.md docs/ops/attendance/start-guide.md tests
git commit -m "feat: implement nz attendance hybrid automation mvp"
```

### Task 6: Final verification and push

**Files:**
- Modify: `README.md`
- Modify: `docs/ops/attendance/start-guide.md`

**Step 1: Перевірити запуск команди**

Run: `PYTHONPATH=src python3 -m school_attendance.cli --help`
Expected: help output with `run-daily` command.

**Step 2: Запустити dry-run e2e на прикладі CSV**

Run: `PYTHONPATH=src python3 -m school_attendance.cli run-daily --dry-run --raw-file <path/to/sample.csv> --run-date 2026-03-04`
Expected: створені `out/2026-03-04/summary.json`, `detail.csv`, `report.md`.

**Step 3: Перевірити git status**

Run: `git status -sb`
Expected: clean working tree.

**Step 4: Push feature branch**

Run: `git push -u origin codex/attendance-app`
Expected: branch available on remote.
