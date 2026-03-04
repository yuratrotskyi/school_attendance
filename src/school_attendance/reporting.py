"""Writers for output attendance reports."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from .models import AttendanceRecord


def write_report_bundle(
    out_dir: Path,
    run_date: date,
    summary: Mapping[str, Mapping[str, object]],
    records: Iterable[AttendanceRecord],
    incidents: Iterable[Mapping[str, object]],
) -> Dict[str, str]:
    """Write summary JSON, details CSV and markdown report bundle."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    detail_path = out_dir / "detail.csv"
    grouped_path = out_dir / "student-absence-summary.csv"
    report_md_path = out_dir / "report.md"
    records_list = list(records)
    incidents_list = list(incidents)
    grouped_rows = _build_student_absence_rows(records_list, summary)

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_detail_csv(detail_path, records_list)
    _write_student_absence_csv(grouped_path, grouped_rows)
    _write_report_markdown(report_md_path, run_date, summary, incidents_list, grouped_rows)

    return {
        "summary_json": str(summary_path),
        "detail_csv": str(detail_path),
        "student_absence_summary_csv": str(grouped_path),
        "report_md": str(report_md_path),
    }


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
                "| Учень | Клас | 7 днів | 30 днів | Семестр |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for row in grouped_list:
            lines.append(
                "| {name} | {klass} | {week_count} | {month_count} | {semester_count} |".format(
                    name=row.get("student_name", "-"),
                    klass=row.get("class_name", "-"),
                    week_count=row.get("week_absent_lessons", 0),
                    month_count=row.get("month_absent_lessons", 0),
                    semester_count=row.get("semester_absent_lessons", 0),
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
        "student_id",
        "student_name",
        "class_name",
        "week_absent_lessons",
        "month_absent_lessons",
        "semester_absent_lessons",
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
                    "week_absent_lessons": row.get("week_absent_lessons", 0),
                    "month_absent_lessons": row.get("month_absent_lessons", 0),
                    "semester_absent_lessons": row.get("semester_absent_lessons", 0),
                }
            )


def _build_student_absence_rows(
    records: Iterable[AttendanceRecord],
    summary: Mapping[str, Mapping[str, object]],
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
            }

        if _in_period(row.lesson_date, bounds["week"]):
            grouped[key]["week_absent_lessons"] = int(grouped[key]["week_absent_lessons"]) + 1
        if _in_period(row.lesson_date, bounds["month"]):
            grouped[key]["month_absent_lessons"] = int(grouped[key]["month_absent_lessons"]) + 1
        if _in_period(row.lesson_date, bounds["semester"]):
            grouped[key]["semester_absent_lessons"] = int(grouped[key]["semester_absent_lessons"]) + 1

    rows = list(grouped.values())
    rows = [
        row
        for row in rows
        if int(row.get("week_absent_lessons", 0))
        or int(row.get("month_absent_lessons", 0))
        or int(row.get("semester_absent_lessons", 0))
    ]
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
