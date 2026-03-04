# NZ Journal List Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Перевести збір відвідуваності на журнали `nz.ua/journal/list` з підтримкою пагінації та правил мапінгу `Н`/`ХВ`.

**Architecture:** `collector` отримує список журналів, обходить кожен журнал і його сторінки, витягує відмітки (API-first, DOM fallback), нормалізує їх у запис уроку, дедуплікує і зберігає raw CSV. `pipeline` працює далі без зміни контракта: парсить CSV, рахує метрики, формує звіти.

**Tech Stack:** Python 3.9+, Playwright sync API, stdlib (`csv`, `json`, `dataclasses`, `datetime`, `typing`, `unittest`).

---

### Task 1: Тести мапінгу позначок і дедуплікації

**Files:**
- Create: `tests/test_collector_journal_records.py`
- Modify: `src/school_attendance/collector.py`

**Step 1: Write the failing test**

```python
def test_map_mark_n_as_absent_and_hv_as_ignored():
    rows = [
        {"mark": "Н", "student_id": "1", "student_name": "A", "class_name": "7-А", "date": "2026-03-04", "lesson_no": 2},
        {"mark": "ХВ", "student_id": "1", "student_name": "A", "class_name": "7-А", "date": "2026-03-04", "lesson_no": 3},
    ]
    got = _normalize_journal_rows(rows, journal_id="j1")
    assert len(got) == 1
    assert got[0]["status"] == "ABSENT"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: FAIL (`_normalize_journal_rows` not found).

**Step 3: Write minimal implementation**

```python
def _normalize_journal_rows(...):
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_collector_journal_records.py src/school_attendance/collector.py
git commit -m "test: add mark mapping and dedup tests for journal records"
```

### Task 2: Тести пагінації журналів

**Files:**
- Modify: `tests/test_collector_journal_records.py`
- Modify: `src/school_attendance/collector.py`

**Step 1: Write the failing test**

```python
def test_collects_links_across_paginated_journal_list():
    pages = [
        {"links": ["j1", "j2"], "next": "p2"},
        {"links": ["j3"], "next": None},
    ]
    got = _collect_paginated_links(pages)
    assert got == ["j1", "j2", "j3"]
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: FAIL (`_collect_paginated_links` not found).

**Step 3: Write minimal implementation**

```python
def _collect_paginated_links(...):
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_collector_journal_records.py src/school_attendance/collector.py
git commit -m "test: add pagination traversal tests for journal list"
```

### Task 3: Реалізація збору з `journal/list` у collector

**Files:**
- Modify: `src/school_attendance/collector.py`
- Modify: `config/nz_selectors.example.json`

**Step 1: Write the failing test**

```python
def test_write_raw_csv_from_normalized_records():
    records = [...]
    path = _write_journal_records_csv(tmp_dir, records)
    assert path.exists()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: FAIL (`_write_journal_records_csv` not found).

**Step 3: Write minimal implementation**

```python
def collect_raw_exports(config, run_date):
    # open /journal/list, traverse journals + pages, normalize, deduplicate, write csv
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_journal_records.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/school_attendance/collector.py config/nz_selectors.example.json tests/test_collector_journal_records.py
git commit -m "feat: collect attendance from nz journal list with pagination"
```

### Task 4: Оновлення документації запуску

**Files:**
- Modify: `README.md`
- Modify: `docs/ops/attendance/start-guide.md`

**Step 1: Write the failing test**

```python
# N/A (documentation task)
```

**Step 2: Run test to verify it fails**

Run: `rg -n "journal/list|Н|ХВ|пагінац" README.md docs/ops/attendance/start-guide.md`
Expected: missing matches before update.

**Step 3: Write minimal implementation**

```markdown
Додати інструкції по source=journal list, правилам позначок і селекторам пагінації.
```

**Step 4: Run test to verify it passes**

Run: `rg -n "journal/list|Н|ХВ|пагінац" README.md docs/ops/attendance/start-guide.md`
Expected: matches present in обох файлах.

**Step 5: Commit**

```bash
git add README.md docs/ops/attendance/start-guide.md
git commit -m "docs: update guide for journal list attendance source"
```

### Task 5: Повна перевірка і push

**Files:**
- Modify: `tests/test_pipeline_dry_run.py` (за потреби)

**Step 1: Write the failing test**

```python
def test_pipeline_still_generates_outputs_with_csv_contract():
    ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_pipeline_dry_run.py -v`
Expected: FAIL only if contract changed unexpectedly.

**Step 3: Write minimal implementation**

```python
# скоригувати pipeline тільки якщо потрібно для нового raw CSV
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/school_attendance tests README.md docs/ops/attendance/start-guide.md config/nz_selectors.example.json
git commit -m "feat: switch attendance source to journal list with pagination support"
git push -u origin codex/attendance-app
```
