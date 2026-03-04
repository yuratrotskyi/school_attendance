"""Manual nz.ua login bootstrap and session-state persistence."""

from __future__ import annotations

from pathlib import Path
import json
import select
import sys
import time
from typing import Callable, Sequence

from .config import AppConfig
from .collector import CollectorError


def bootstrap_session(config: AppConfig, timeout_seconds: int = 300) -> Path:
    """Open browser for manual login and save storage state.

    This command is designed for environments where automated login can be
    challenged by anti-bot protection.
    """

    if not config.selectors_path or not config.selectors_path.exists():
        raise CollectorError("Selector config file is required (SELECTORS_PATH)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CollectorError(
            "Playwright is not installed. Run: pip install -r requirements.txt && playwright install chromium"
        ) from exc

    selector_cfg = json.loads(config.selectors_path.read_text(encoding="utf-8"))
    login_url = selector_cfg.get("login_url", config.base_url)
    open_login_button_selector = selector_cfg.get("open_login_button_selector")
    open_login_wait_ms = int(selector_cfg.get("open_login_wait_ms", 1200))
    auth_success_selectors = selector_cfg.get("auth_success_selectors", [])

    session_state_path = config.session_state_path
    session_state_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        launch_kwargs = {
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if config.browser_channel:
            launch_kwargs["channel"] = config.browser_channel
        browser = pw.chromium.launch(**launch_kwargs)
        context = browser.new_context()
        page = context.new_page()

        page.goto(login_url, wait_until="domcontentloaded")
        if open_login_button_selector:
            page.click(open_login_button_selector)
            page.wait_for_timeout(open_login_wait_ms)

        print("Виконайте ручний вхід у відкритому браузері, потім поверніться в термінал.")
        print("Натисніть Enter у терміналі для ручного збереження сесії або дочекайтеся авто-виявлення входу.")

        if auth_success_selectors:
            _wait_for_bootstrap_confirmation(
                page=page,
                auth_success_selectors=auth_success_selectors,
                timeout_seconds=timeout_seconds,
                manual_enter_detector=_manual_enter_pressed,
            )
            context.storage_state(path=str(session_state_path))
            context.close()
            browser.close()
            return session_state_path

        input("Після успішного входу натисніть Enter для збереження сесії...")
        context.storage_state(path=str(session_state_path))
        context.close()
        browser.close()

    return session_state_path


def _wait_for_bootstrap_confirmation(
    page,
    auth_success_selectors: Sequence[str],
    timeout_seconds: int,
    manual_enter_detector: Callable[[], bool],
) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if any(page.locator(sel).count() > 0 for sel in auth_success_selectors):
            return "selector"
        if manual_enter_detector():
            return "manual"
        page.wait_for_timeout(1000)

    raise CollectorError("Timeout waiting for authenticated page state")


def _manual_enter_pressed() -> bool:
    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0)
    except Exception:
        return False

    if not readable:
        return False

    try:
        sys.stdin.readline()
    except Exception:
        return False
    return True
