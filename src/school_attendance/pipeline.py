"""Pipeline orchestration for daily attendance reporting."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
import shutil
from typing import Dict, Iterable, List, Optional

from .analytics import (
    build_period_summary,
    build_student_risk_list,
    build_ten_day_absence_periods,
    detect_escape_incidents,
)
from .collector import collect_raw_exports
from .config import AppConfig
from .models import AttendanceRecord
from .parser import parse_attendance_csv
from .reporting import write_report_bundle


def run_daily(
    config: AppConfig,
    run_date: date,
    dry_run: bool = False,
    skip_collect: bool = False,
    raw_files: Optional[Iterable[Path]] = None,
) -> Dict[str, object]:
    """Run daily attendance pipeline and return artifact metadata."""

    run_raw_dir = config.data_dir / "raw" / run_date.isoformat()
    run_norm_dir = config.data_dir / "normalized" / run_date.isoformat()
    run_proc_dir = config.data_dir / "processed" / run_date.isoformat()
    run_out_dir = config.out_dir / run_date.isoformat()

    _reset_run_directory(run_raw_dir)
    _reset_run_directory(run_norm_dir)
    _reset_run_directory(run_proc_dir)
    _reset_run_directory(run_out_dir)

    files: List[Path] = [Path(p) for p in raw_files] if raw_files else []

    if not skip_collect and not dry_run:
        collected = collect_raw_exports(config, run_date)
        files.extend(collected)

    if not files:
        raise ValueError("No raw files provided. Use --raw-file or run without --skip-collect.")

    all_records: List[AttendanceRecord] = []
    for file_path in files:
        all_records.extend(parse_attendance_csv(file_path))

    _write_normalized_csv(run_norm_dir / "attendance.csv", all_records)

    incidents = detect_escape_incidents(all_records, excused_codes=config.excused_codes)
    summary = build_period_summary(
        all_records,
        run_date=run_date,
        semester_start=config.semester_start,
        excused_codes=config.excused_codes,
    )

    week_start = run_date.fromordinal(run_date.toordinal() - 6)
    risk_students = build_student_risk_list(
        all_records,
        start=week_start,
        end=run_date,
        risk_threshold=config.risk_threshold,
    )
    summary["week"]["risk_students"] = len(risk_students)
    ten_day_summary, ten_day_periods = build_ten_day_absence_periods(
        records=all_records,
        semester_start=config.semester_start,
        run_date=run_date,
        min_learning_days=10,
    )

    _write_incidents_csv(run_proc_dir / "incidents.csv", incidents)

    paths = write_report_bundle(
        out_dir=run_out_dir,
        run_date=run_date,
        summary=summary,
        records=all_records,
        incidents=incidents,
        ten_day_summary=ten_day_summary,
        ten_day_periods=ten_day_periods,
    )

    return {
        "run_date": run_date.isoformat(),
        "record_count": len(all_records),
        "incident_count": len(incidents),
        "risk_student_count": len(risk_students),
        "paths": paths,
    }


def _write_normalized_csv(path: Path, records: Iterable[AttendanceRecord]) -> None:
    fields = ["student_id", "student_name", "class", "date", "lesson_no", "status", "reason_code"]
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


def _reset_run_directory(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def _write_incidents_csv(path: Path, incidents: Iterable[Dict[str, object]]) -> None:
    fields = [
        "student_id",
        "student_name",
        "class_name",
        "lesson_date",
        "start_lesson",
        "consecutive_absences",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in incidents:
            writer.writerow(
                {
                    "student_id": row.get("student_id", ""),
                    "student_name": row.get("student_name", ""),
                    "class_name": row.get("class_name", ""),
                    "lesson_date": row.get("lesson_date", ""),
                    "start_lesson": row.get("start_lesson", ""),
                    "consecutive_absences": row.get("consecutive_absences", ""),
                }
            )
