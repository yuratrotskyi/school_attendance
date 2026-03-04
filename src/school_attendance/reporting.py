"""Writers for output attendance reports."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

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
    report_md_path = out_dir / "report.md"

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_detail_csv(detail_path, records)
    _write_report_markdown(report_md_path, run_date, summary, incidents)

    return {
        "summary_json": str(summary_path),
        "detail_csv": str(detail_path),
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
) -> None:
    incidents_list: List[Mapping[str, object]] = list(incidents)
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
        "## Інциденти \"втік з уроків\"",
    ]

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
