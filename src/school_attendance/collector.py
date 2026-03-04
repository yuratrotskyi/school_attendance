"""Data collection from nz.ua via browser automation (hybrid mode)."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import AppConfig


class CollectorError(RuntimeError):
    """Raised when collection could not be completed."""


def _build_context_kwargs(config: AppConfig) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"accept_downloads": True}
    if config.session_state_path.exists():
        kwargs["storage_state"] = str(config.session_state_path)
    return kwargs


def collect_raw_exports(config: AppConfig, run_date: date) -> List[Path]:
    """Collect raw export files from nz.ua.

    Requires a selector config JSON because nz.ua interface may change.
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
    exports = selector_cfg.get("exports", [])
    if not exports:
        raise CollectorError("Selector config has no export definitions")

    run_dir = config.data_dir / "raw" / run_date.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)

    downloaded_files: List[Path] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(**_build_context_kwargs(config))
        page = context.new_page()

        login_url = selector_cfg.get("login_url", f"{config.base_url}/login")
        login_selector = selector_cfg.get("login_selector", 'input[name="login"]')

        page.goto(login_url, wait_until="domcontentloaded")
        page.wait_for_timeout(int(selector_cfg.get("pre_login_wait_ms", 1200)))

        if _requires_login(page, login_selector, selector_cfg):
            if not config.nz_login or not config.nz_password:
                raise CollectorError(
                    "Session is not authenticated and NZ_LOGIN/NZ_PASSWORD are missing. "
                    "Run bootstrap-session first or provide credentials."
                )

            page.fill(login_selector, config.nz_login)
            page.fill(selector_cfg.get("password_selector", 'input[name="password"]'), config.nz_password)
            page.click(selector_cfg.get("submit_selector", 'button[type="submit"]'))
            page.wait_for_timeout(int(selector_cfg.get("post_login_wait_ms", 2000)))

        for item in exports:
            name = item["name"]
            page.goto(item["url"], wait_until="domcontentloaded")
            with page.expect_download(timeout=int(item.get("timeout_ms", 30000))) as download_info:
                page.click(item["download_button_selector"])
            download = download_info.value
            target = run_dir / f"{name}-{download.suggested_filename}"
            download.save_as(str(target))
            downloaded_files.append(target)

        context.close()
        browser.close()

    return downloaded_files


def _requires_login(page, login_selector: str, selector_cfg: Dict[str, Any]) -> bool:
    """Return True when login form is present and requires credential auth."""

    if page.locator(login_selector).count() > 0:
        return True

    open_login_button_selector = selector_cfg.get("open_login_button_selector")
    if not open_login_button_selector:
        return False

    if page.locator(open_login_button_selector).count() > 0:
        page.click(open_login_button_selector)
        page.wait_for_timeout(int(selector_cfg.get("open_login_wait_ms", 1200)))

    return page.locator(login_selector).count() > 0
