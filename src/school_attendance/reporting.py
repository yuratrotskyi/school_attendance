"""Writers for output attendance reports."""

from __future__ import annotations

import csv
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
from xml.sax.saxutils import escape

from .models import AttendanceRecord


def write_attendance_10plus_report_bundle(
    out_dir: Path,
    rows: Iterable[Mapping[str, object]],
) -> Dict[str, str]:
    """Write dedicated attendance-overview 10+ absence report files."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "періоди-відсутності-10-днів-відвідуваність.csv"
    xlsx_path = out_dir / "періоди-відсутності-10-днів-відвідуваність.xlsx"
    rows_list = list(rows)

    _write_attendance_10plus_csv(csv_path, rows_list)
    _write_attendance_10plus_xlsx(xlsx_path, rows_list)

    return {
        "attendance_10plus_csv": str(csv_path),
        "attendance_10plus_xlsx": str(xlsx_path),
    }


def write_report_bundle(
    out_dir: Path,
    run_date: date,
    summary: Mapping[str, Mapping[str, object]],
    records: Iterable[AttendanceRecord],
    incidents: Iterable[Mapping[str, object]],
    ten_day_summary: Optional[Mapping[str, Mapping[str, object]]] = None,
    ten_day_periods: Optional[Iterable[Mapping[str, object]]] = None,
    class_daily_absence: Optional[Mapping[str, object]] = None,
) -> Dict[str, str]:
    """Write summary JSON, details CSV and markdown report bundle."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    detail_path = out_dir / "detail.csv"
    detail_xlsx_path = out_dir / "detail.xlsx"
    grouped_path = out_dir / "student-absence-summary.csv"
    grouped_xlsx_path = out_dir / "student-absence-summary.xlsx"
    report_md_path = out_dir / "report.md"
    ten_day_periods_path = out_dir / "ten-day-absence-periods.csv"
    ten_day_periods_xlsx_path = out_dir / "періоди-відсутності-10-днів.xlsx"
    class_daily_absence_path = out_dir / "відсутність-сьогодні-вчора.csv"
    class_daily_absence_xlsx_path = out_dir / "відсутність-сьогодні-вчора.xlsx"
    records_list = list(records)
    incidents_list = list(incidents)
    ten_day_summary_map = ten_day_summary or {}
    ten_day_periods_list = list(ten_day_periods or [])
    class_daily_absence_data = class_daily_absence or {"total_today": 0, "total_yesterday": 0, "rows": []}
    grouped_rows = _build_student_absence_rows(records_list, summary, ten_day_summary_map)

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_detail_csv(detail_path, records_list)
    _write_detail_xlsx(detail_xlsx_path, records_list)
    _write_student_absence_csv(grouped_path, grouped_rows)
    _write_student_absence_xlsx(grouped_xlsx_path, grouped_rows)
    _write_report_markdown(report_md_path, run_date, summary, incidents_list, grouped_rows)
    _write_class_absence_today_yesterday_csv(class_daily_absence_path, class_daily_absence_data)
    _write_class_absence_today_yesterday_xlsx(class_daily_absence_xlsx_path, class_daily_absence_data)

    paths = {
        "summary_json": str(summary_path),
        "detail_csv": str(detail_path),
        "detail_xlsx": str(detail_xlsx_path),
        "student_absence_summary_csv": str(grouped_path),
        "student_absence_summary_xlsx": str(grouped_xlsx_path),
        "report_md": str(report_md_path),
        "class_absence_today_yesterday_csv": str(class_daily_absence_path),
        "class_absence_today_yesterday_xlsx": str(class_daily_absence_xlsx_path),
    }
    if ten_day_periods_list:
        _write_ten_day_periods_csv(ten_day_periods_path, ten_day_periods_list)
        _write_ten_day_periods_xlsx(ten_day_periods_xlsx_path, ten_day_periods_list)
        paths["ten_day_absence_periods_csv"] = str(ten_day_periods_path)
        paths["ten_day_absence_periods_xlsx"] = str(ten_day_periods_xlsx_path)

    return paths


def _write_detail_csv(path: Path, records: Iterable[AttendanceRecord]) -> None:
    fields = [
        "student_id",
        "student_name",
        "class",
        "date",
        "lesson_no",
        "status",
        "reason_code",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "student_id": row.student_id,
                    "student_name": row.student_name,
                    "class": row.class_name,
                    "date": row.lesson_date.isoformat(),
                    "lesson_no": row.lesson_no,
                    "status": row.status,
                    "reason_code": row.reason_code,
                }
            )


def _write_detail_xlsx(path: Path, records: Iterable[AttendanceRecord]) -> None:
    headers = [
        "student_id",
        "student_name",
        "class",
        "date",
        "lesson_no",
        "status",
        "reason_code",
    ]
    rows = [
        [
            row.student_id,
            row.student_name,
            row.class_name,
            row.lesson_date.isoformat(),
            row.lesson_no,
            row.status,
            row.reason_code,
        ]
        for row in records
    ]
    _write_xlsx_table(path, headers=headers, rows=rows, sheet_title="detail")


def _write_report_markdown(
    path: Path,
    run_date: date,
    summary: Mapping[str, Mapping[str, object]],
    incidents: Iterable[Mapping[str, object]],
    student_absence_rows: Iterable[Mapping[str, object]],
) -> None:
    incidents_list: List[Mapping[str, object]] = list(incidents)
    grouped_list: List[Mapping[str, object]] = list(student_absence_rows)
    week = summary.get("week", {})
    month = summary.get("month", {})
    semester = summary.get("semester", {})

    lines = [
        "# Щоденний звіт відвідуваності",
        "",
        f"Дата формування: {run_date.isoformat()}",
        "",
        "## KPI",
        f"- Пропущених уроків (7 днів): {week.get('absent_lessons', 0)}",
        f"- Пропущених уроків (30 днів): {month.get('absent_lessons', 0)}",
        f"- Пропущених уроків (семестр): {semester.get('absent_lessons', 0)}",
        "",
        "## Пропуски по учнях (Н)",
    ]

    if not grouped_list:
        lines.append("- Немає пропусків.")
    else:
        lines.extend(
            [
                "| Учень | Клас | 7 днів | 30 днів | Семестр | 10+ періодів (семестр) | Останній 10+ період (від-до) |",
                "|---|---|---:|---:|---:|---:|---|",
            ]
        )
        for row in grouped_list:
            lines.append(
                "| {name} | {klass} | {week_count} | {month_count} | {semester_count} | {periods_count} | {last_period} |".format(
                    name=row.get("student_name", "-"),
                    klass=row.get("class_name", "-"),
                    week_count=row.get("week_absent_lessons", 0),
                    month_count=row.get("month_absent_lessons", 0),
                    semester_count=row.get("semester_absent_lessons", 0),
                    periods_count=row.get("ten_plus_periods_count", 0),
                    last_period=row.get("last_ten_plus_period", "-"),
                )
            )

    lines.extend(
        [
            "",
        "## Інциденти \"втік з уроків\"",
        ]
    )

    if not incidents_list:
        lines.append("- Немає інцидентів.")
    else:
        for incident in incidents_list:
            lines.append(
                "- {name} ({klass}) дата {day}, урок {lesson}, підряд {count}".format(
                    name=incident.get("student_name", "-"),
                    klass=incident.get("class_name", "-"),
                    day=incident.get("lesson_date", "-"),
                    lesson=incident.get("start_lesson", "-"),
                    count=incident.get("consecutive_absences", "-"),
                )
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_student_absence_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    fields = [
        "ID учня",
        "Учень",
        "Клас",
        "Н (7 днів)",
        "Н (30 днів)",
        "Н",
        "К-сть періодів 10+",
        "Останній період 10+ (від-до)",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ID учня": row.get("student_id", ""),
                    "Учень": row.get("student_name", ""),
                    "Клас": row.get("class_name", ""),
                    "Н (7 днів)": row.get("week_absent_lessons", 0),
                    "Н (30 днів)": row.get("month_absent_lessons", 0),
                    "Н": row.get("semester_absent_lessons", 0),
                    "К-сть періодів 10+": row.get("ten_plus_periods_count", 0),
                    "Останній період 10+ (від-до)": row.get("last_ten_plus_period", "-"),
                }
            )


def _write_student_absence_xlsx(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    headers = [
        "ID учня",
        "Учень",
        "Клас",
        "Н (7 днів)",
        "Н (30 днів)",
        "Н",
        "К-сть періодів 10+",
        "Останній період 10+ (від-до)",
    ]
    xlsx_rows = [
        [
            row.get("student_id", ""),
            row.get("student_name", ""),
            row.get("class_name", ""),
            row.get("week_absent_lessons", 0),
            row.get("month_absent_lessons", 0),
            row.get("semester_absent_lessons", 0),
            row.get("ten_plus_periods_count", 0),
            row.get("last_ten_plus_period", "-"),
        ]
        for row in rows
    ]
    _write_xlsx_table(path, headers=headers, rows=xlsx_rows, sheet_title="Учні")


def _build_student_absence_rows(
    records: Iterable[AttendanceRecord],
    summary: Mapping[str, Mapping[str, object]],
    ten_day_summary: Mapping[str, Mapping[str, object]],
) -> List[Dict[str, object]]:
    bounds = {
        "week": _extract_period_bounds(summary, "week"),
        "month": _extract_period_bounds(summary, "month"),
        "semester": _extract_period_bounds(summary, "semester"),
    }
    grouped: Dict[Tuple[str, str, str], Dict[str, object]] = {}

    for row in records:
        if row.status != "ABSENT":
            continue

        key = (row.student_id, row.student_name, row.class_name)
        if key not in grouped:
            grouped[key] = {
                "student_id": row.student_id,
                "student_name": row.student_name,
                "class_name": row.class_name,
                "week_absent_lessons": 0,
                "month_absent_lessons": 0,
                "semester_absent_lessons": 0,
                "ten_plus_periods_count": 0,
                "last_ten_plus_period": "-",
                "_week_days": set(),
                "_month_days": set(),
                "_semester_days": set(),
            }

        if _in_period(row.lesson_date, bounds["week"]):
            grouped[key]["_week_days"].add(row.lesson_date)  # type: ignore[attr-defined]
        if _in_period(row.lesson_date, bounds["month"]):
            grouped[key]["_month_days"].add(row.lesson_date)  # type: ignore[attr-defined]
        if _in_period(row.lesson_date, bounds["semester"]):
            grouped[key]["_semester_days"].add(row.lesson_date)  # type: ignore[attr-defined]

    rows = list(grouped.values())
    for row in rows:
        row["week_absent_lessons"] = len(row.pop("_week_days", set()))
        row["month_absent_lessons"] = len(row.pop("_month_days", set()))
        row["semester_absent_lessons"] = len(row.pop("_semester_days", set()))
    rows = [
        row
        for row in rows
        if int(row.get("week_absent_lessons", 0))
        or int(row.get("month_absent_lessons", 0))
        or int(row.get("semester_absent_lessons", 0))
    ]
    for row in rows:
        student_id = str(row.get("student_id", ""))
        student_name = str(row.get("student_name", ""))
        class_name = str(row.get("class_name", ""))
        identity_key = _student_identity_key(student_id=student_id, student_name=student_name, class_name=class_name)
        ten_day = ten_day_summary.get(identity_key) or ten_day_summary.get(student_id, {})
        count = int(ten_day.get("ten_plus_periods_count", 0) or 0)
        start = str(ten_day.get("last_period_start", "") or "").strip()
        end = str(ten_day.get("last_period_end", "") or "").strip()
        period_text = f"{start} - {end}" if start and end else "-"
        row["ten_plus_periods_count"] = count
        row["last_ten_plus_period"] = period_text

    rows.sort(
        key=lambda row: (
            -int(row.get("semester_absent_lessons", 0)),
            -int(row.get("month_absent_lessons", 0)),
            -int(row.get("week_absent_lessons", 0)),
            str(row.get("class_name", "")),
            str(row.get("student_name", "")),
        )
    )
    return rows


def _write_ten_day_periods_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    fields = [
        "student_id",
        "student_name",
        "class_name",
        "period_start",
        "period_end",
        "learning_days_absent",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "student_id": row.get("student_id", ""),
                    "student_name": row.get("student_name", ""),
                    "class_name": row.get("class_name", ""),
                    "period_start": row.get("period_start", ""),
                    "period_end": row.get("period_end", ""),
                    "learning_days_absent": row.get("learning_days_absent", 0),
                }
            )


def _write_ten_day_periods_xlsx(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    headers = [
        "ID учня",
        "Учень",
        "Клас",
        "Період від",
        "Період до",
        "К-сть навчальних днів",
    ]
    xlsx_rows = [
        [
            row.get("student_id", ""),
            row.get("student_name", ""),
            row.get("class_name", ""),
            row.get("period_start", ""),
            row.get("period_end", ""),
            row.get("learning_days_absent", 0),
        ]
        for row in rows
    ]
    _write_xlsx_table(path, headers=headers, rows=xlsx_rows, sheet_title="10+ періоди")


def _write_attendance_10plus_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    fields = [
        "ID учня",
        "Учень",
        "Клас",
        "Період від",
        "Період до",
        "К-сть навчальних днів",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ID учня": row.get("student_id", ""),
                    "Учень": row.get("student_name", ""),
                    "Клас": row.get("class_name", ""),
                    "Період від": row.get("period_start", ""),
                    "Період до": row.get("period_end", ""),
                    "К-сть навчальних днів": row.get("learning_days_absent", 0),
                }
            )


def _write_attendance_10plus_xlsx(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    headers = [
        "ID учня",
        "Учень",
        "Клас",
        "Період від",
        "Період до",
        "К-сть навчальних днів",
    ]
    xlsx_rows = [
        [
            row.get("student_id", ""),
            row.get("student_name", ""),
            row.get("class_name", ""),
            row.get("period_start", ""),
            row.get("period_end", ""),
            row.get("learning_days_absent", 0),
        ]
        for row in rows
    ]
    _write_xlsx_table(path, headers=headers, rows=xlsx_rows, sheet_title="10+ відсутність")


def _write_class_absence_today_yesterday_csv(path: Path, data: Mapping[str, object]) -> None:
    rows = list(data.get("rows", []) or [])
    total_today = int(data.get("total_today", 0) or 0)
    total_yesterday = int(data.get("total_yesterday", 0) or 0)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["клас", "к-сть сьогодні", "к-сть вчора"])
        writer.writerow(["усього", total_today, total_yesterday])
        for row in rows:
            writer.writerow(
                [
                    row.get("class_name", ""),
                    int(row.get("today_count", 0) or 0),
                    int(row.get("yesterday_count", 0) or 0),
                ]
            )


def _write_class_absence_today_yesterday_xlsx(path: Path, data: Mapping[str, object]) -> None:
    rows = list(data.get("rows", []) or [])
    total_today = int(data.get("total_today", 0) or 0)
    total_yesterday = int(data.get("total_yesterday", 0) or 0)
    xlsx_rows: List[List[object]] = [["усього", total_today, total_yesterday]]
    xlsx_rows.extend(
        [
            [
                row.get("class_name", ""),
                int(row.get("today_count", 0) or 0),
                int(row.get("yesterday_count", 0) or 0),
            ]
            for row in rows
        ]
    )
    _write_xlsx_table(
        path,
        headers=["клас", "к-сть сьогодні", "к-сть вчора"],
        rows=xlsx_rows,
        sheet_title="Класи",
    )


def _write_xlsx_table(
    path: Path,
    headers: Iterable[object],
    rows: Iterable[Iterable[object]],
    sheet_title: str,
) -> None:
    safe_sheet_title = _sanitize_sheet_title(sheet_title)
    worksheet_xml = _build_worksheet_xml([list(headers)] + [list(row) for row in rows])
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(safe_sheet_title)}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    package_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", package_rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


def _build_worksheet_xml(rows: Iterable[Iterable[object]]) -> str:
    rendered_rows = []
    for row_index, row in enumerate(rows, start=1):
        rendered_cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_excel_column_name(column_index)}{row_index}"
            rendered_cells.append(_build_cell_xml(cell_ref, value))
        rendered_rows.append(f'<row r="{row_index}">{"".join(rendered_cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(rendered_rows)}</sheetData>'
        "</worksheet>"
    )


def _build_cell_xml(cell_ref: str, value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    text = escape(str(value if value is not None else ""))
    return f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _excel_column_name(index: int) -> str:
    letters = []
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def _sanitize_sheet_title(title: str) -> str:
    sanitized = "".join("_" if char in '[]:*?/\\' else char for char in str(title or "Sheet1"))
    sanitized = sanitized[:31].strip()
    return sanitized or "Sheet1"


def _extract_period_bounds(
    summary: Mapping[str, Mapping[str, object]],
    period_name: str,
) -> Optional[Tuple[date, date]]:
    period = summary.get(period_name, {})
    start = _parse_iso_date(period.get("period_start"))
    end = _parse_iso_date(period.get("period_end"))
    if not start or not end:
        return None
    return (start, end)


def _parse_iso_date(raw: object) -> Optional[date]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _in_period(day: date, bounds: Optional[Tuple[date, date]]) -> bool:
    if not bounds:
        return False
    start, end = bounds
    return start <= day <= end


def _student_identity_key(student_id: str, student_name: str, class_name: str) -> str:
    return f"{student_id}::{student_name}::{class_name}"
