# NZ Session Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Додати одноразовий ручний вхід у nz.ua зі збереженням browser session state і повторним використанням цієї сесії під час `run-daily`.

**Architecture:** Вводиться новий модуль `session_bootstrap.py` та команда CLI `bootstrap-session`. Конфіг розширюється полем `session_state_path`, а collector спочатку пробує працювати з файлом сесії і лише потім fallback-логіном через форму.

**Tech Stack:** Python 3.9+, argparse, dataclasses, Playwright sync API, unittest.

---

### Task 1: TDD для CLI команди bootstrap-session

**Files:**
- Create: `tests/test_cli_bootstrap_command.py`
- Modify: `src/school_attendance/cli.py`

**Step 1: Write the failing test**

```python
def test_bootstrap_command_dispatches_handler():
    ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_cli_bootstrap_command.py -v`
Expected: FAIL (unknown command/handler missing).

**Step 3: Write minimal implementation**

```python
# add subcommand and handler invocation
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_cli_bootstrap_command.py -v`
Expected: PASS.

### Task 2: TDD для config поля session_state_path

**Files:**
- Create: `tests/test_config_session_path.py`
- Modify: `src/school_attendance/config.py`
- Modify: `.env.example`

**Step 1: Write the failing test**

```python
def test_load_config_uses_default_session_state_path():
    ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_config_session_path.py -v`
Expected: FAIL (field missing).

**Step 3: Write minimal implementation**

```python
session_state_path=Path(os.getenv("SESSION_STATE_PATH", "config/nz_session_state.json"))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_config_session_path.py -v`
Expected: PASS.

### Task 3: Реалізація session bootstrap модуля

**Files:**
- Create: `src/school_attendance/session_bootstrap.py`
- Modify: `config/nz_selectors.example.json`

**Step 1: Add manual login bootstrap function**

```python
def bootstrap_session(config, timeout_seconds=300):
    ...
```

**Step 2: Add save/timeout flow and minimal validation**

```python
# wait for user confirmation or auth selector
```

**Step 3: Verify module import**

Run: `PYTHONPATH=src python3 -c "from school_attendance.session_bootstrap import bootstrap_session; print('ok')"`
Expected: `ok`.

### Task 4: Collector session reuse

**Files:**
- Create: `tests/test_collector_session_logic.py`
- Modify: `src/school_attendance/collector.py`

**Step 1: Write failing unit tests for pure helper logic**

```python
def test_build_context_kwargs_with_existing_session_file():
    ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_session_logic.py -v`
Expected: FAIL.

**Step 3: Implement helper + collector integration**

```python
def _build_context_kwargs(config):
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python3 -m unittest tests/test_collector_session_logic.py -v`
Expected: PASS.

### Task 5: Final verification and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/ops/attendance/start-guide.md`
- Modify: `.gitignore`

**Step 1: Run full tests**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS.

**Step 2: Verify CLI help includes bootstrap-session**

Run: `PYTHONPATH=src python3 -m school_attendance.cli --help`
Expected: command list contains `bootstrap-session`.

**Step 3: Commit and push**

```bash
git add ...
git commit -m "feat: add manual nz session bootstrap and reuse"
git push
```
