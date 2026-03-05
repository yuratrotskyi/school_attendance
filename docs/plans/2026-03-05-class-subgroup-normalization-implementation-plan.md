# Class Subgroup Normalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Normalize class names by removing parenthesized suffixes so subgroup variants are merged into a single class.

**Architecture:** Add one shared normalization helper and call it from collector and parser. Validate behavior with focused unit tests in parser and collector suites.

**Tech Stack:** Python 3.9, stdlib `re`, unittest.

---

### Task 1: Add shared class normalization helper

**Files:**
- Create: `src/school_attendance/classname.py`
- Test: `tests/test_parser.py`

**Step 1: Write failing test**
- Add parser test where input class is `8-В (ІІ підгрупа)` and expected `AttendanceRecord.class_name` is `8-В`.

**Step 2: Run test to verify fail**
- `PYTHONPATH=src python3 -m unittest tests.test_parser.TestParserAndReporting.test_parse_attendance_csv_normalizes_class_subgroup_suffix -v`

**Step 3: Implement helper**
- `normalize_class_name(raw: str) -> str` with regex-based parenthesis stripping and whitespace cleanup.

**Step 4: Make parser use helper**
- Normalize `class_name` in `parse_attendance_csv`.

**Step 5: Re-run targeted test**
- Same command, expected PASS.

### Task 2: Apply helper in collector

**Files:**
- Modify: `src/school_attendance/collector.py`
- Test: `tests/test_collector_journal_records.py`

**Step 1: Write failing tests**
- Validate class extraction output removes suffix from title/header.
- Validate normalized journal rows output class without parenthesized suffix.

**Step 2: Run tests to verify fail**
- `PYTHONPATH=src python3 -m unittest tests.test_collector_journal_records.TestCollectorJournalRecords.test_extract_class_name_hint_from_title_and_header_text tests.test_collector_journal_records.TestCollectorJournalRecords.test_normalize_journal_rows_normalizes_class_name -v`

**Step 3: Implement minimal changes**
- Normalize class hints and row class names with shared helper.

**Step 4: Re-run targeted tests**
- Same command, expected PASS.

### Task 3: Regression verification

**Files:**
- Verify: `tests/`

**Step 1: Run full suite**
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`

**Step 2: Commit**
- `git add ...`
- `git commit -m "fix: normalize class subgroup names"`
