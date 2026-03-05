"""Parsers for attendance data exports."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .classname import normalize_class_name
from .models import AttendanceRecord


_HEADER_ALIASES = {
    "student_id": ["student_id", "id", "uid", "ID учня", "ID"],
    "student_name": ["student_name", "name", "ПІБ", "Учень"],
    "class_name": ["class", "class_name", "Клас"],
    "date": ["date", "Дата"],
    "lesson_no": ["lesson_no", "lesson", "Урок", "№ уроку"],
    "status": ["status", "Статус", "Відмітка"],
    "reason_code": ["reason_code", "Причина", "Код причини"],
}

_PRESENT_VALUES = {"P", "PRESENT", "+", "П", "ПРИСУТНІЙ"}
_ABSENT_VALUES = {"A", "ABSENT", "Н", "ВІДСУТНІЙ"}


def parse_attendance_csv(path: Path) -> List[AttendanceRecord]:
    """Parse attendance CSV export into normalized records."""

    path = Path(path)
    records: List[AttendanceRecord] = []

    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        mapping = _resolve_header_mapping(reader.fieldnames or [])
        for row in reader:
            status = _normalize_status(row[mapping["status"]])
            reason_code = (row.get(mapping["reason_code"], "") or "").strip()
            records.append(
                AttendanceRecord(
                    student_id=(row[mapping["student_id"]] or "").strip(),
                    student_name=(row[mapping["student_name"]] or "").strip(),
                    class_name=normalize_class_name(row[mapping["class_name"]]),
                    lesson_date=_parse_date(row[mapping["date"]]),
                    lesson_no=int((row[mapping["lesson_no"]] or "0").strip()),
                    status=status,
                    reason_code=reason_code,
                )
            )

    return records


def _resolve_header_mapping(headers: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for target, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in headers:
                mapping[target] = alias
                break
        if target not in mapping:
            raise ValueError(f"Required column missing: {target}")
    return mapping


def _parse_date(value: str):
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def _normalize_status(value: str) -> str:
    token = (value or "").strip().upper()
    if token in _PRESENT_VALUES:
        return "PRESENT"
    if token in _ABSENT_VALUES:
        return "ABSENT"
    raise ValueError(f"Unsupported status value: {value}")
