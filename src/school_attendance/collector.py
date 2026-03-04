"""Data collection from nz.ua via browser automation (hybrid mode)."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Dict, List

from .config import AppConfig


class CollectorError(RuntimeError):
    """Raised when collection could not be completed."""


def collect_raw_exports(config: AppConfig, run_date: date) -> List[Path]:
    """Collect raw export files from nz.ua.

    Requires a selector config JSON because nz.ua interface may change.
    """

    if not config.nz_login or not config.nz_password:
        raise CollectorError("NZ_LOGIN and NZ_PASSWORD are required for collection")

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
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(selector_cfg.get("login_url", f"{config.base_url}/login"), wait_until="domcontentloaded")
        open_login_button_selector = selector_cfg.get("open_login_button_selector")
        if open_login_button_selector:
            page.click(open_login_button_selector)
            page.wait_for_timeout(int(selector_cfg.get("open_login_wait_ms", 1200)))

        page.fill(selector_cfg.get("login_selector", 'input[name="login"]'), config.nz_login)
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
