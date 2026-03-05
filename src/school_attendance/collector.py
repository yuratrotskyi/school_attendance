"""Data collection from nz.ua via browser automation (journal list source)."""

from __future__ import annotations

import csv
from datetime import date, datetime
import html
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence
from urllib.parse import parse_qs, urljoin, urlparse

from .classname import normalize_class_name
from .config import AppConfig


class CollectorError(RuntimeError):
    """Raised when collection could not be completed."""


_UK_MONTH_MAP = {
    "січ": 1,
    "лют": 2,
    "бер": 3,
    "квіт": 4,
    "трав": 5,
    "черв": 6,
    "лип": 7,
    "серп": 8,
    "вер": 9,
    "жовт": 10,
    "лист": 11,
    "груд": 12,
}


def _build_context_kwargs(config: AppConfig) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"accept_downloads": True}
    if config.session_state_path.exists():
        kwargs["storage_state"] = str(config.session_state_path)
    return kwargs


def _build_launch_kwargs(config: AppConfig) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "headless": config.nz_headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if config.browser_channel:
        kwargs["channel"] = config.browser_channel
    return kwargs


def collect_raw_exports(config: AppConfig, run_date: date) -> List[Path]:
    """Collect raw attendance file from nz.ua journal list.

    Requires selector config JSON because nz.ua interface may change.
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

    run_dir = config.data_dir / "raw" / run_date.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**_build_launch_kwargs(config))
        context = browser.new_context(**_build_context_kwargs(config))
        page = context.new_page()

        _ensure_authenticated(page=page, config=config, selector_cfg=selector_cfg)

        records = _collect_journal_attendance_records(page=page, config=config, selector_cfg=selector_cfg)
        if not records:
            raise CollectorError("No attendance records collected from journal pages")

        raw_csv = _write_journal_records_csv(run_dir=run_dir, records=records)
        context.storage_state(path=str(config.session_state_path))

        context.close()
        browser.close()

    return [raw_csv]


def _ensure_authenticated(page: Any, config: AppConfig, selector_cfg: Dict[str, Any]) -> None:
    login_url = selector_cfg.get("login_url", f"{config.base_url}/")
    login_selector = selector_cfg.get("login_selector", 'input[name="login"]')

    page.goto(login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(int(selector_cfg.get("pre_login_wait_ms", 1200)))
    _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="login")

    if not _requires_login(page, login_selector, selector_cfg):
        return

    if not config.nz_login or not config.nz_password:
        raise CollectorError(
            "Session is not authenticated and NZ_LOGIN/NZ_PASSWORD are missing. "
            "Run bootstrap-session first or provide credentials."
        )

    page.fill(login_selector, config.nz_login)
    page.fill(selector_cfg.get("password_selector", 'input[name="password"]'), config.nz_password)
    page.click(selector_cfg.get("submit_selector", 'button[type="submit"]'))
    page.wait_for_timeout(int(selector_cfg.get("post_login_wait_ms", 2500)))
    _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="post-login")

    if _requires_login(page, login_selector, {"open_login_button_selector": None}):
        raise CollectorError("Login to nz.ua failed: login form is still visible after submit")


def _collect_journal_attendance_records(page: Any, config: AppConfig, selector_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    journal_cfg = selector_cfg.get("journal_list", {})
    list_url = journal_cfg.get("url", f"{config.base_url}/journal/list")

    journal_urls = _collect_journal_links(
        page=page,
        list_url=list_url,
        base_url=config.base_url,
        list_cfg=journal_cfg,
        config=config,
        selector_cfg=selector_cfg,
    )
    if not journal_urls:
        _write_debug_artifacts(page=page, logs_dir=config.logs_dir, stem="journal-list-no-links")
        raise CollectorError(
            "No journal links found on /journal/list. "
            "Update config.journal_list.link_selector or check logs/artifacts for journal-list-no-links*.html"
        )

    all_records: List[Dict[str, Any]] = []
    empty_debug_written = 0
    for journal_url in journal_urls:
        try:
            rows = _collect_single_journal_records(
                page=page,
                journal_url=journal_url,
                base_url=config.base_url,
                selector_cfg=selector_cfg,
                config=config,
            )
        except CollectorError:
            raise
        except Exception as exc:
            print(f"[collector] Skip journal {journal_url}: {exc}")
            continue
        if not rows:
            if empty_debug_written < 3:
                journal_id = _extract_journal_id(journal_url)
                _write_debug_artifacts(page=page, logs_dir=config.logs_dir, stem=f"journal-empty-{journal_id}")
                empty_debug_written += 1
            continue
        all_records.extend(rows)

    deduped = _deduplicate_normalized_records(all_records)
    if not deduped:
        _write_text_artifact(
            logs_dir=config.logs_dir,
            stem="journal-no-records",
            content="\n".join(journal_urls),
            suffix="urls.txt",
        )
    return deduped


def _collect_journal_links(
    page: Any,
    list_url: str,
    base_url: str,
    list_cfg: Dict[str, Any],
    config: AppConfig,
    selector_cfg: Dict[str, Any],
) -> List[str]:
    link_selector = list_cfg.get("link_selector", 'a[href*="/journal/"]')
    next_selector = list_cfg.get("next_page_selector", ".pagination a[rel='next'], .pagination li.next a")
    wait_ms = int(list_cfg.get("wait_ms", 1300))
    max_pages = int(list_cfg.get("max_pages", 50))

    pages: List[Dict[str, Any]] = []
    current_url: Optional[str] = list_url
    visited: set = set()
    click_discovery_urls: List[str] = []

    for _ in range(max_pages):
        if not current_url or current_url in visited:
            break
        visited.add(current_url)

        page.goto(current_url, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="journal-list")

        if _is_journal_href(page.url):
            return _collect_paginated_links(pages=[{"links": [page.url], "next": None}], base_url=base_url)

        links = _extract_links_from_page(page=page, link_selector=link_selector, list_url=list_url)
        if not links:
            discovered = _discover_journal_links_by_click(
                page=page,
                list_cfg=list_cfg,
                list_url=list_url,
                config=config,
                selector_cfg=selector_cfg,
            )
            click_discovery_urls.extend(discovered)

        next_url = _extract_next_href(
            page=page,
            next_selector=next_selector,
            current_url=page.url,
            base_url=base_url,
        )

        pages.append({"links": links, "next": next_url})
        current_url = next_url

    if click_discovery_urls:
        pages.append({"links": click_discovery_urls, "next": None})

    return _collect_paginated_links(pages=pages, base_url=base_url)


def _extract_links_from_page(page: Any, link_selector: str, list_url: str) -> List[str]:
    raw_values: List[str] = []
    locator = page.locator(link_selector)
    count = locator.count()
    if count == 0 and link_selector != "a":
        locator = page.locator("a")
        count = locator.count()

    for idx in range(count):
        node = locator.nth(idx)
        href = (node.get_attribute("href") or "").strip()
        data_href = (node.get_attribute("data-href") or node.get_attribute("data-url") or "").strip()
        onclick = (node.get_attribute("onclick") or "").strip()
        raw_values.extend([href, data_href, onclick])

    try:
        attr_values = page.eval_on_selector_all(
            "[href], [data-href], [data-url], [onclick]",
            "els => els.flatMap(el => [el.getAttribute('href'), el.getAttribute('data-href'), el.getAttribute('data-url'), el.getAttribute('onclick')]).filter(Boolean)",
        )
        raw_values.extend(str(value) for value in attr_values)
    except Exception:
        pass

    try:
        raw_values.append(page.content())
    except Exception:
        pass

    return _extract_candidate_journal_hrefs(raw_values)


def _discover_journal_links_by_click(
    page: Any,
    list_cfg: Dict[str, Any],
    list_url: str,
    config: AppConfig,
    selector_cfg: Dict[str, Any],
) -> List[str]:
    chip_selector = list_cfg.get("chip_selector", "table tbody tr td:nth-child(2) *")
    wait_ms = int(list_cfg.get("click_wait_ms", 1500))
    max_clicks = int(list_cfg.get("max_chip_clicks", 200))

    labels = _collect_clickable_chip_labels(page=page, chip_selector=chip_selector, max_clicks=max_clicks)
    found: List[str] = []

    for label in labels:
        try:
            page.goto(list_url, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="journal-list-click")
        except Exception:
            continue

        candidates = page.locator(chip_selector).filter(has_text=label)
        if candidates.count() == 0:
            continue

        clicked = candidates.first
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=6000):
                clicked.click(force=True)
        except Exception:
            try:
                clicked.click(force=True)
            except Exception:
                continue
            page.wait_for_timeout(wait_ms)
        _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="journal-open")

        found.extend(_extract_candidate_journal_hrefs([page.url]))

        try:
            current_href = str(page.evaluate("() => window.location.href"))
            found.extend(_extract_candidate_journal_hrefs([current_href]))
        except Exception:
            pass

        try:
            perf_urls = page.evaluate("() => performance.getEntriesByType('resource').map(x => x.name)")
            found.extend(_extract_candidate_journal_hrefs(str(item) for item in perf_urls))
        except Exception:
            pass

    return found


def _collect_clickable_chip_labels(page: Any, chip_selector: str, max_clicks: int) -> List[str]:
    labels: List[str] = []
    seen: set = set()
    locator = page.locator(chip_selector)
    count = min(locator.count(), max_clicks)

    for idx in range(count):
        text = _safe_locator_text(locator.nth(idx))
        if not _looks_like_class_chip_label(text):
            continue
        normalized = " ".join(text.split())
        if normalized in seen:
            continue
        seen.add(normalized)
        labels.append(normalized)

    return labels


def _extract_candidate_journal_hrefs(raw_values: Iterable[str]) -> List[str]:
    found: List[str] = []
    seen: set = set()
    token_pattern = re.compile(
        r"https?://[^\"'\s<>]+|/[A-Za-z0-9_./?=&%#:-]+|journal\?[A-Za-z0-9_./?=&%#:-]+|journal/[A-Za-z0-9_./?=&%#:-]+"
    )

    for raw in raw_values:
        if raw is None:
            continue
        text = str(raw).replace("\\/", "/")
        candidates = [text]
        candidates.extend(token_pattern.findall(text))

        for candidate in candidates:
            value = candidate.strip().strip("\"'`;,()[]{}")
            if not value or value in seen:
                continue
            if not _is_journal_href(value):
                continue
            seen.add(value)
            found.append(value)

    return found


def _is_journal_href(href: str) -> bool:
    text = (href or "").strip()
    if not text:
        return False

    normalized = text.lower().replace("\\/", "/")
    if "journal" not in normalized:
        return False
    if "journal/list" in normalized:
        return False

    parsed = urlparse(normalized if "://" in normalized or normalized.startswith("/") else f"/{normalized}")
    path = parsed.path.strip("/")

    if re.search(r"(^|/)journal($|/)", path):
        if re.search(r"(^|/)journal/list($|/)", path):
            return False
        return True

    return (
        normalized.startswith("journal?")
        or "/journal?" in normalized
        or "journal?" in normalized
        or "/journal/" in normalized
        or "journal/" in normalized
    )


def _looks_like_class_chip_label(text: str) -> bool:
    token = " ".join((text or "").split())
    if not token:
        return False
    if len(token) > 48:
        return False
    if "-" not in token:
        return False
    if not re.search(r"\d", token):
        return False
    return bool(re.search(r"[A-Za-zА-Яа-яІіЇїЄєҐґ]", token))


def _write_debug_artifacts(page: Any, logs_dir: Path, stem: str) -> None:
    artifacts_dir = logs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    html_path = artifacts_dir / f"{stem}-{timestamp}.html"
    url_path = artifacts_dir / f"{stem}-{timestamp}.url.txt"
    screenshot_path = artifacts_dir / f"{stem}-{timestamp}.png"

    try:
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception:
        pass

    try:
        url_path.write_text(str(page.url), encoding="utf-8")
    except Exception:
        pass

    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        pass


def _write_text_artifact(logs_dir: Path, stem: str, content: str, suffix: str = "txt") -> None:
    artifacts_dir = logs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = artifacts_dir / f"{stem}-{timestamp}.{suffix}"
    path.write_text(content, encoding="utf-8")


def _is_cloudflare_challenge_title(title: str) -> bool:
    token = (title or "").strip().lower()
    return "just a moment" in token or "security verification" in token


def _is_cloudflare_challenge_html(html: str) -> bool:
    token = (html or "").lower()
    markers = [
        "cf-turnstile-response",
        "/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/",
        "performing security verification",
        "just a moment",
        "verify you are human",
        "__cf_chl_f_tk=",
        "__cf_chl_rt_tk=",
    ]
    return any(marker in token for marker in markers)


def _is_cloudflare_challenge_page(page: Any) -> bool:
    try:
        if _is_cloudflare_challenge_title(page.title()):
            return True
    except Exception:
        pass

    try:
        return _is_cloudflare_challenge_html(page.content())
    except Exception:
        return False


def _ensure_not_cloudflare_blocked(page: Any, config: AppConfig, selector_cfg: Dict[str, Any], stage: str) -> None:
    if not _is_cloudflare_challenge_page(page):
        return

    wait_seconds = int(selector_cfg.get("cloudflare_wait_seconds", config.cloudflare_wait_seconds))
    notice_after_seconds = int(selector_cfg.get("cloudflare_notice_after_seconds", 5))
    notice_after_seconds = max(0, notice_after_seconds)
    if config.nz_headless:
        _write_debug_artifacts(page=page, logs_dir=config.logs_dir, stem=f"cloudflare-{stage}")
        raise CollectorError(
            "Cloudflare verification is blocking automated collection in headless mode. "
            "Set NZ_HEADLESS=false, run bootstrap-session once, then run-daily again."
        )

    notice_printed = False
    for second in range(max(1, wait_seconds)):
        if not _is_cloudflare_challenge_page(page):
            return
        if not notice_printed and second >= notice_after_seconds:
            print("[collector] Cloudflare verification detected. Complete checkbox in opened browser window...")
            notice_printed = True
        page.wait_for_timeout(1000)

    if not _is_cloudflare_challenge_page(page):
        return

    _write_debug_artifacts(page=page, logs_dir=config.logs_dir, stem=f"cloudflare-timeout-{stage}")
    raise CollectorError(
        f"Cloudflare verification not completed within {wait_seconds}s at stage '{stage}'. "
        "Open logs/artifacts/cloudflare-timeout-*.html to inspect."
    )


def _collect_single_journal_records(
    page: Any,
    journal_url: str,
    base_url: str,
    selector_cfg: Dict[str, Any],
    config: AppConfig,
) -> List[Dict[str, Any]]:
    page_cfg = selector_cfg.get("journal_page", {})
    next_selector = page_cfg.get("next_page_selector", ".pagination a[rel='next'], .pagination li.next a")
    wait_ms = int(page_cfg.get("wait_ms", 1300))
    max_pages = int(page_cfg.get("max_pages", 20))

    journal_id = _extract_journal_id(journal_url)
    class_name_hint = ""
    raw_rows: List[Dict[str, Any]] = []
    anchored_to_first_page = False

    current_url: Optional[str] = journal_url
    visited: set = set()

    for _ in range(max_pages):
        if not current_url or current_url in visited:
            break
        visited.add(current_url)

        page.goto(current_url, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)
        _ensure_not_cloudflare_blocked(page=page, config=config, selector_cfg=selector_cfg, stage="journal-page")

        if not anchored_to_first_page:
            anchored_to_first_page = True
            first_url = _extract_first_href(page=page, current_url=page.url, base_url=base_url)
            if first_url and not _urls_equal(first_url, page.url):
                visited.discard(current_url)
                current_url = first_url
                continue

        if not class_name_hint:
            class_name_hint = _extract_class_name(page=page, page_cfg=page_cfg)

        page_rows = _collect_current_page_rows(page=page, page_cfg=page_cfg, class_name_hint=class_name_hint)
        raw_rows.extend(page_rows)

        next_url = _extract_next_href(
            page=page,
            next_selector=next_selector,
            current_url=page.url,
            base_url=base_url,
        )
        current_url = next_url

    normalized = _normalize_journal_rows(raw_rows=raw_rows, journal_id=journal_id)
    normalized_hint = normalize_class_name(class_name_hint)
    if normalized_hint:
        for row in normalized:
            if not row["class_name"]:
                row["class_name"] = normalized_hint
    return normalized


def _collect_current_page_rows(page: Any, page_cfg: Dict[str, Any], class_name_hint: str) -> List[Dict[str, Any]]:
    if page_cfg.get("api_first", True):
        api_rows = _extract_rows_from_window_state(page=page, class_name_hint=class_name_hint)
        if api_rows:
            return api_rows

    return _extract_rows_from_dom(page=page, page_cfg=page_cfg, class_name_hint=class_name_hint)


def _extract_rows_from_window_state(page: Any, class_name_hint: str) -> List[Dict[str, Any]]:
    try:
        payload = page.evaluate(
            """() => window.__INITIAL_STATE__ || window.__NUXT__ || window.__NEXT_DATA__ || null"""
        )
    except Exception:
        return []

    if payload is None:
        return []

    return _extract_rows_from_api_payload(payload=payload, class_name_hint=class_name_hint)


def _extract_rows_from_api_payload(payload: Any, class_name_hint: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for node in _walk_dicts(payload):
        student_name = _pick_text(node, ["student_name", "studentName", "student", "pupil_name", "name"])
        date_text = _pick_text(node, ["date", "lesson_date", "day"])
        lesson_no = _pick_int(node, ["lesson_no", "lessonNo", "lesson", "number"])
        mark = _pick_text(node, ["mark", "attendance_mark", "attendance", "value", "status"])
        if not student_name or not date_text or lesson_no is None or mark is None:
            continue

        student_id = _pick_text(node, ["student_id", "studentId", "pupil_id", "uid", "id"]) or _synthetic_student_id(
            student_name
        )
        class_name = _pick_text(node, ["class_name", "className", "class"]) or class_name_hint

        rows.append(
            {
                "student_id": student_id,
                "student_name": student_name,
                "class_name": class_name,
                "date": date_text,
                "lesson_no": lesson_no,
                "mark": mark,
            }
        )

    return rows


def _walk_dicts(payload: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _walk_dicts(value)
        return

    if isinstance(payload, list):
        for item in payload:
            yield from _walk_dicts(item)


def _pick_text(node: Dict[str, Any], keys: Sequence[str]) -> Optional[str]:
    for key in keys:
        if key not in node:
            continue
        value = node.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _pick_int(node: Dict[str, Any], keys: Sequence[str]) -> Optional[int]:
    for key in keys:
        if key not in node:
            continue
        parsed = _to_int(node.get(key))
        if parsed is not None:
            return parsed
    return None


def _extract_rows_from_dom(page: Any, page_cfg: Dict[str, Any], class_name_hint: str) -> List[Dict[str, Any]]:
    row_selector = page_cfg.get("row_selector", "table tbody tr")
    student_name_selector = page_cfg.get("student_name_selector", "td:nth-child(1)")
    student_id_attr = page_cfg.get("student_id_attr", "data-student-id")
    mark_cell_selector = page_cfg.get("mark_cell_selector", "td[data-date]")
    mark_date_attr = page_cfg.get("mark_date_attr", "data-date")
    mark_lesson_attr = page_cfg.get("mark_lesson_attr", "data-lesson-no")
    mark_text_attr = page_cfg.get("mark_text_attr")

    rows: List[Dict[str, Any]] = []
    row_locator = page.locator(row_selector)
    row_count = row_locator.count()

    for row_idx in range(row_count):
        row = row_locator.nth(row_idx)
        student_name = _safe_locator_text(row.locator(student_name_selector).first)
        if not student_name:
            continue

        student_id = (row.get_attribute(student_id_attr) or "").strip() or _synthetic_student_id(student_name)
        mark_cells = row.locator(mark_cell_selector)
        mark_count = mark_cells.count()

        for cell_idx in range(mark_count):
            cell = mark_cells.nth(cell_idx)
            date_text = (cell.get_attribute(mark_date_attr) or "").strip()
            if not date_text:
                continue

            lesson_no = _to_int(cell.get_attribute(mark_lesson_attr) or str(cell_idx + 1))
            if lesson_no is None:
                continue

            mark = ""
            if mark_text_attr:
                mark = (cell.get_attribute(mark_text_attr) or "").strip()
            if not mark:
                mark = _safe_locator_text(cell)

            rows.append(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "class_name": class_name_hint,
                    "date": date_text,
                    "lesson_no": lesson_no,
                    "mark": mark,
                }
            )

    if rows:
        return rows

    return _extract_rows_from_dom_grid(page=page, class_name_hint=class_name_hint)


def _extract_rows_from_dom_grid(page: Any, class_name_hint: str) -> List[Dict[str, Any]]:
    payload = _extract_attendance_grid_payload(page)
    if not payload:
        return []

    day_headers = payload.get("day_headers", [])
    month_headers = payload.get("month_headers", [])
    body_rows = payload.get("rows", [])
    name_col_idx = _to_int(payload.get("name_col_idx"))
    if name_col_idx is None:
        name_col_idx = 1

    semester_bounds = _extract_semester_bounds_from_text(payload.get("page_text", ""))
    topics_dates = _extract_dates_from_topics(payload.get("topic_dates", []), semester_bounds)
    column_meta = _build_grid_column_meta(
        day_headers=day_headers,
        month_headers=month_headers,
        semester_bounds=semester_bounds,
        topics_dates=topics_dates,
    )
    if not column_meta:
        return []

    rows: List[Dict[str, Any]] = []
    for cells in body_rows:
        if not isinstance(cells, list) or name_col_idx >= len(cells):
            continue

        student_name = str(cells[name_col_idx]).strip()
        if not student_name or student_name == "ПІБ учня":
            continue

        student_id = _synthetic_student_id(student_name)
        for item in column_meta:
            col_idx = item["col_idx"]
            if col_idx >= len(cells):
                continue
            rows.append(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "class_name": class_name_hint,
                    "date": item["date"],
                    "lesson_no": item["lesson_no"],
                    "mark": str(cells[col_idx]).strip(),
                }
            )

    return rows


def _extract_attendance_grid_payload(page: Any) -> Optional[Dict[str, Any]]:
    try:
        return page.evaluate(
            """() => {
                const norm = (v) => (v || '').replace(/\\s+/g, ' ').trim();
                const tables = Array.from(document.querySelectorAll('table'));

                let best = null;
                let bestScore = -1;
                for (const table of tables) {
                    const text = norm(table.innerText);
                    let score = 0;
                    if (text.includes('ПІБ учня')) score += 5;
                    if (text.includes('№ уроку')) score -= 3;
                    if ((table.querySelectorAll('tbody tr').length || 0) > 5) score += 1;
                    if (score > bestScore) {
                        bestScore = score;
                        best = table;
                    }
                }

                if (!best || bestScore < 3) {
                    return null;
                }

                const headerRows = Array.from(best.querySelectorAll('thead tr'));
                const dayRow = headerRows.length ? headerRows[headerRows.length - 1] : null;
                const monthRow = headerRows.length > 1 ? headerRows[0] : null;
                const dayHeaders = dayRow ? Array.from(dayRow.children).map(c => norm(c.innerText)) : [];
                const monthHeaders = monthRow
                    ? Array.from(monthRow.children).map(c => ({ text: norm(c.innerText), span: Number(c.getAttribute('colspan') || 1) }))
                    : [];

                let nameColIdx = dayHeaders.findIndex(text => text.toLowerCase().includes('піб'));
                if (nameColIdx < 0) {
                    nameColIdx = 1;
                }

                const bodyRows = Array.from(best.querySelectorAll('tbody tr')).map(row =>
                    Array.from(row.children).map(cell => {
                        const input = cell.querySelector('input.mark-cell, input[value]');
                        if (input) {
                            const val = norm(input.value);
                            if (val) return val;
                        }
                        return norm(cell.innerText);
                    })
                );

                const topicTable = tables.find(table => {
                    const text = norm(table.innerText);
                    return text.includes('Дата') && text.includes('№ уроку') && text.includes('Домаш');
                });

                let topicDates = [];
                if (topicTable) {
                    const headCells = Array.from(topicTable.querySelectorAll('thead tr:last-child th, thead tr:last-child td'))
                        .map(cell => norm(cell.innerText));
                    const dateIdx = headCells.findIndex(text => text.toLowerCase().includes('дата'));
                    const lessonIdx = headCells.findIndex(text => text.toLowerCase().includes('№ урок'));

                    if (dateIdx >= 0) {
                        topicDates = Array.from(topicTable.querySelectorAll('tbody tr'))
                            .map(row => Array.from(row.children).map(cell => norm(cell.innerText)))
                            .map(cells => ({
                                date_text: cells[dateIdx] || '',
                                lesson_no: lessonIdx >= 0 ? cells[lessonIdx] || '' : '',
                            }))
                            .filter(item => item.date_text);
                    }
                }

                return {
                    day_headers: dayHeaders,
                    month_headers: monthHeaders,
                    rows: bodyRows,
                    name_col_idx: nameColIdx,
                    topic_dates: topicDates,
                    page_text: norm(document.body ? document.body.innerText : ''),
                };
            }"""
        )
    except Exception:
        return None


def _build_grid_column_meta(
    day_headers: List[Any],
    month_headers: List[Dict[str, Any]],
    semester_bounds: Optional[Sequence[str]],
    topics_dates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    day_tokens = [str(item).strip() for item in day_headers]
    day_numbers = [_extract_day_number(token) for token in day_tokens]
    attendance_col_indexes = [idx for idx, day in enumerate(day_numbers) if day is not None]

    if not attendance_col_indexes:
        start_idx = 2 if len(day_tokens) > 2 else 0
        attendance_col_indexes = list(range(start_idx, len(day_tokens)))

    if not attendance_col_indexes:
        return []

    expanded_months = _expand_month_headers(month_headers, len(day_tokens))
    meta: List[Dict[str, Any]] = []
    current_month: Optional[int] = None

    for pos, col_idx in enumerate(attendance_col_indexes):
        if pos < len(topics_dates):
            date_iso = topics_dates[pos]["date"]
            lesson_no = topics_dates[pos]["lesson_no"]
        else:
            day_value = day_numbers[col_idx] if col_idx < len(day_numbers) else None
            month_token = day_tokens[col_idx]
            month_no = _month_number_from_token(month_token)
            if month_no is None and col_idx < len(expanded_months):
                month_no = _month_number_from_token(expanded_months[col_idx])
            if month_no is None:
                month_no = current_month
            if month_no is not None:
                current_month = month_no
            date_iso = _resolve_date_from_day_and_month(day_value, month_no, semester_bounds)
            lesson_no = pos + 1

        if not date_iso:
            continue

        meta.append(
            {
                "col_idx": col_idx,
                "date": date_iso,
                "lesson_no": lesson_no,
            }
        )

    return meta


def _expand_month_headers(month_headers: List[Dict[str, Any]], total_columns: int) -> List[str]:
    expanded: List[str] = []
    for item in month_headers:
        text = str(item.get("text", "")).strip()
        span = _to_int(item.get("span"))
        if span is None or span <= 0:
            span = 1
        expanded.extend([text] * span)

    if len(expanded) < total_columns:
        last = expanded[-1] if expanded else ""
        expanded.extend([last] * (total_columns - len(expanded)))
    elif len(expanded) > total_columns:
        expanded = expanded[:total_columns]

    return expanded


def _extract_semester_bounds_from_text(text: str) -> Optional[Sequence[str]]:
    token = str(text or "")
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*[-–]\s*(\d{2}\.\d{2}\.\d{4})", token)
    if not match:
        return None

    start = _normalize_date(match.group(1))
    end = _normalize_date(match.group(2))
    if not start or not end:
        return None

    return (start, end)


def _extract_dates_from_topics(topics: List[Dict[str, Any]], semester_bounds: Optional[Sequence[str]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in topics:
        date_iso = _normalize_topic_date(item.get("date_text"), semester_bounds)
        lesson_no = _to_int(item.get("lesson_no"))
        if not date_iso:
            continue
        result.append(
            {
                "date": date_iso,
                "lesson_no": lesson_no if lesson_no is not None else (len(result) + 1),
            }
        )
    return result


def _normalize_topic_date(text: Any, semester_bounds: Optional[Sequence[str]]) -> Optional[str]:
    raw = str(text or "").strip()
    if not raw:
        return None

    parsed_iso = _normalize_date(raw)
    if parsed_iso:
        return parsed_iso

    match = re.search(r"(\d{1,2})\s+([A-Za-zА-Яа-яІіЇїЄєҐґ\.]+)", raw)
    if not match:
        return None

    return _resolve_date_from_day_and_month(match.group(1), match.group(2), semester_bounds)


def _resolve_date_from_day_and_month(
    day_token: Any,
    month_token: Any,
    semester_bounds: Optional[Sequence[str]],
) -> Optional[str]:
    day = _to_int(day_token)
    month = _month_number_from_token(month_token)
    if day is None or month is None:
        return None

    year = _resolve_year_for_month(month=month, semester_bounds=semester_bounds)
    if year is None:
        year = datetime.now().year

    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def _month_number_from_token(token: Any) -> Optional[int]:
    if isinstance(token, int):
        return token if 1 <= token <= 12 else None

    value = str(token or "").strip().lower().replace(".", "")
    if not value:
        return None

    for part in re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ]+", value):
        for key, month in _UK_MONTH_MAP.items():
            if part.startswith(key):
                return month
    return None


def _extract_day_number(token: Any) -> Optional[int]:
    match = re.search(r"\b(\d{1,2})\b", str(token or ""))
    if not match:
        return None
    day = _to_int(match.group(1))
    if day is None or day < 1 or day > 31:
        return None
    return day


def _resolve_year_for_month(month: int, semester_bounds: Optional[Sequence[str]]) -> Optional[int]:
    if not semester_bounds or len(semester_bounds) != 2:
        return None

    start_iso = _normalize_date(semester_bounds[0])
    end_iso = _normalize_date(semester_bounds[1])
    if not start_iso or not end_iso:
        return None

    start_date = datetime.strptime(start_iso, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_iso, "%Y-%m-%d").date()

    if start_date.year == end_date.year:
        return start_date.year
    return start_date.year if month >= start_date.month else end_date.year


def _extract_class_name(page: Any, page_cfg: Dict[str, Any]) -> str:
    selector = page_cfg.get("class_name_selector", "h1")
    if selector:
        locator = page.locator(selector)
        if locator.count() > 0:
            text = _safe_locator_text(locator.first)
            parsed = _extract_class_name_hint(text)
            if parsed:
                return normalize_class_name(parsed)

    try:
        parsed_title = _extract_class_name_hint(page.title())
        if parsed_title:
            return normalize_class_name(parsed_title)
    except Exception:
        pass

    return ""


def _extract_class_name_hint(text: Any) -> str:
    token = " ".join(str(text or "").split())
    if not token:
        return ""

    patterns = [
        r"журнал оцінок для\s+(.+?)(?:\s*\[[^\]]*\]|$)",
        r"журнал\s+(.+?)(?:\s*\||$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, token, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip(" :-")
        if value:
            return normalize_class_name(value)

    class_match = re.search(r"\b\d{1,2}\s*[-–]\s*[A-Za-zА-Яа-яІіЇїЄєҐґ](?:\s*\([^)]*\))?", token)
    if class_match:
        return normalize_class_name(class_match.group(0).strip())
    return ""


def _extract_next_href(page: Any, next_selector: str, current_url: str, base_url: str) -> Optional[str]:
    locator = page.locator(next_selector)
    hrefs: List[str] = []

    if locator.count() > 0:
        for idx in range(locator.count()):
            href = (locator.nth(idx).get_attribute("href") or "").strip()
            if href:
                hrefs.append(href)

    if not hrefs:
        try:
            hrefs = page.eval_on_selector_all(
                ".pagination a, nav a[aria-label*='next'], a[rel='next']",
                "els => els.map(el => el.getAttribute('href')).filter(Boolean)",
            )
        except Exception:
            hrefs = []

    return _pick_next_pagination_href(current_url=current_url, hrefs=hrefs, base_url=base_url)


def _extract_first_href(page: Any, current_url: str, base_url: str) -> Optional[str]:
    hrefs: List[str] = []

    try:
        hrefs = page.eval_on_selector_all(
            ".pagination a, nav a[aria-label*='page'], a[rel='prev'], a[rel='next']",
            "els => els.map(el => el.getAttribute('href')).filter(Boolean)",
        )
    except Exception:
        hrefs = []

    return _pick_first_pagination_href(current_url=current_url, hrefs=hrefs, base_url=base_url)


def _pick_next_pagination_href(current_url: str, hrefs: Iterable[str], base_url: str) -> Optional[str]:
    normalized_links = _normalize_pagination_hrefs(hrefs=hrefs, base_url=base_url)

    if not normalized_links:
        return None

    current_page = _extract_page_number(current_url)
    ranked: List[tuple] = []
    for link in normalized_links:
        if _urls_equal(link, current_url):
            continue
        link_page = _extract_page_number(link)
        if current_page is not None and link_page is not None and link_page > current_page:
            ranked.append((link_page, link))

    if ranked:
        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    for link in normalized_links:
        if not _urls_equal(link, current_url):
            return link
    return None


def _pick_first_pagination_href(current_url: str, hrefs: Iterable[str], base_url: str) -> Optional[str]:
    normalized_links = _normalize_pagination_hrefs(hrefs=hrefs, base_url=base_url)
    if not normalized_links:
        return None

    current_page = _extract_page_number(current_url)
    page_links: List[tuple] = []
    for link in normalized_links:
        link_page = _extract_page_number(link)
        if link_page is None:
            continue
        page_links.append((link_page, link))

    if not page_links:
        return None

    page_links.sort(key=lambda item: item[0])

    if current_page is None:
        for page_no, link in page_links:
            if page_no == 1:
                return link
        return None

    for page_no, link in page_links:
        if page_no < current_page:
            return link
    return None


def _normalize_pagination_hrefs(hrefs: Iterable[str], base_url: str) -> List[str]:
    normalized_links: List[str] = []
    seen: set = set()
    for raw_href in hrefs:
        url = urljoin(base_url, str(raw_href).strip())
        if not url or url in seen:
            continue
        seen.add(url)
        normalized_links.append(url)
    return normalized_links


def _urls_equal(first: str, second: str) -> bool:
    return _canonical_url(first) == _canonical_url(second)


def _canonical_url(value: str) -> str:
    parsed = urlparse(str(value or ""))
    query_pairs = parse_qs(parsed.query)
    query_parts = []
    for key in sorted(query_pairs.keys()):
        for val in sorted(query_pairs[key]):
            query_parts.append(f"{key}={val}")
    query = "&".join(query_parts)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}".rstrip("?")


def _extract_page_number(url: str) -> Optional[int]:
    parsed = urlparse(str(url or ""))
    query = parse_qs(parsed.query)
    for key in ("page", "p", "pg"):
        if key in query and query[key]:
            page_no = _to_int(query[key][0])
            if page_no is not None:
                return page_no
    return None


def _extract_journal_id(journal_url: str) -> str:
    parsed = urlparse(journal_url)
    query = parse_qs(parsed.query)
    if "id" in query and query["id"]:
        return query["id"][0]

    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        return parts[-1]
    return journal_url


def _normalize_journal_rows(raw_rows: Iterable[Dict[str, Any]], journal_id: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen: set = set()

    for row in raw_rows:
        student_name = str(row.get("student_name", "")).strip()
        if not student_name:
            continue

        student_id = str(row.get("student_id", "")).strip() or _synthetic_student_id(student_name)
        class_name = normalize_class_name(row.get("class_name", ""))
        date_iso = _normalize_date(row.get("date"))
        lesson_no = _to_int(row.get("lesson_no"))
        if not date_iso or lesson_no is None:
            continue

        status = _map_mark_to_status(row.get("mark"))
        if status is None:
            continue

        key = (journal_id, student_id, date_iso, lesson_no)
        if key in seen:
            continue
        seen.add(key)

        normalized.append(
            {
                "student_id": student_id,
                "student_name": student_name,
                "class_name": class_name,
                "date": date_iso,
                "lesson_no": lesson_no,
                "status": status,
                "reason_code": "",
            }
        )

    normalized.sort(key=lambda r: (r["class_name"], r["student_name"], r["date"], r["lesson_no"]))
    return normalized


def _map_mark_to_status(mark: Any) -> Optional[str]:
    token = str(mark or "").strip().upper()

    if token == "Н":
        return "ABSENT"
    if token == "ХВ":
        return None
    return "PRESENT"


def _normalize_date(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]

    return None


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _synthetic_student_id(student_name: str) -> str:
    cleaned = "".join(ch for ch in student_name.lower() if ch.isalnum())
    return f"name-{cleaned}" if cleaned else "name-unknown"


def _deduplicate_normalized_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set = set()

    for row in records:
        key = (row.get("student_id"), row.get("date"), row.get("lesson_no"), row.get("class_name"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    deduped.sort(key=lambda r: (r.get("class_name", ""), r.get("student_name", ""), r.get("date", ""), r.get("lesson_no", 0)))
    return deduped


def _write_journal_records_csv(run_dir: Path, records: Iterable[Dict[str, Any]]) -> Path:
    path = run_dir / "attendance-journal.csv"
    fields = ["student_id", "student_name", "class", "date", "lesson_no", "status", "reason_code"]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "student_id": row.get("student_id", ""),
                    "student_name": row.get("student_name", ""),
                    "class": row.get("class_name", ""),
                    "date": row.get("date", ""),
                    "lesson_no": row.get("lesson_no", ""),
                    "status": row.get("status", ""),
                    "reason_code": row.get("reason_code", ""),
                }
            )

    return path


def _collect_paginated_links(pages: Iterable[Dict[str, Any]], base_url: str) -> List[str]:
    links: List[str] = []
    seen: set = set()

    for page in pages:
        for raw_link in page.get("links", []):
            url = _normalize_collectable_journal_url(raw_link=raw_link, base_url=base_url)
            if not url or url in seen:
                continue
            seen.add(url)
            links.append(url)

    return links


def _normalize_collectable_journal_url(raw_link: Any, base_url: str) -> Optional[str]:
    raw = html.unescape(str(raw_link or "").strip())
    if not raw:
        return None

    url = urljoin(base_url, raw)
    if not _is_collectable_journal_url(url):
        return None
    return _canonical_url(url)


def _is_collectable_journal_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    path = parsed.path.lower().rstrip("/")
    query = parse_qs(parsed.query)

    if not path.startswith("/journal"):
        return False

    blocked_paths = (
        "/journal/list",
        "/journal/create",
        "/journal/edit",
        "/journal/edit-subgroup",
        "/journal/add-edit-lesson",
        "/journal/export-xls",
        "/journal/export-pdf",
        "/journal/calculate-rating",
        "/journal/calculate-nus",
        "/journal/import-xls",
    )
    if path in blocked_paths:
        return False

    if re.fullmatch(r"/journal/\d+", path):
        return True
    if path == "/journal":
        return bool(query.get("id") or query.get("journal"))
    if path == "/journal/index":
        return bool(query.get("id") or query.get("journal"))
    return False


def _safe_locator_text(locator: Any) -> str:
    try:
        return (locator.inner_text() or "").strip()
    except Exception:
        return ""


def _requires_login(page: Any, login_selector: str, selector_cfg: Dict[str, Any]) -> bool:
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
