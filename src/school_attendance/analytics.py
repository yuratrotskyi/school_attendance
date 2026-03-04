"""Attendance analytics and incident detection."""

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, Iterable, List, Sequence, Set

from .models import AttendanceRecord


def detect_escape_incidents(
    records: Sequence[AttendanceRecord],
    excused_codes: Set[str],
    count_pending_as_unexcused: bool = False,
) -> List[Dict[str, object]]:
    """Detect "escaped from lesson" incidents according to 1+ rule.

    Rule: a student has an incident when, after first presence on the same day,
    they have at least one unexcused absence.
    """

    grouped = defaultdict(list)
    for record in records:
        grouped[(record.student_id, record.lesson_date)].append(record)

    incidents: List[Dict[str, object]] = []
    for (_, lesson_date), student_records in grouped.items():
        ordered = sorted(student_records, key=lambda r: r.lesson_no)
        seen_presence = False
        current_start = None
        current_count = 0

        for row in ordered:
            if row.status == "PRESENT":
                seen_presence = True
                if current_start is not None:
                    incidents.append(_incident_payload(ordered[0], lesson_date, current_start, current_count))
                    current_start = None
                    current_count = 0
                continue

            if row.status != "ABSENT":
                continue

            if not seen_presence:
                continue

            if _is_excused(row.reason_code, excused_codes, count_pending_as_unexcused):
                if current_start is not None:
                    incidents.append(_incident_payload(ordered[0], lesson_date, current_start, current_count))
                    current_start = None
                    current_count = 0
                continue

            if current_start is None:
                current_start = row.lesson_no
                current_count = 1
            elif row.lesson_no == current_start + current_count:
                current_count += 1
            else:
                incidents.append(_incident_payload(ordered[0], lesson_date, current_start, current_count))
                current_start = row.lesson_no
                current_count = 1

        if current_start is not None:
            incidents.append(_incident_payload(ordered[0], lesson_date, current_start, current_count))

    incidents.sort(key=lambda r: (r["lesson_date"], r["class_name"], r["student_name"], r["start_lesson"]))
    return incidents


def _incident_payload(
    first_record: AttendanceRecord,
    lesson_date: date,
    start_lesson: int,
    consecutive_absences: int,
) -> Dict[str, object]:
    return {
        "student_id": first_record.student_id,
        "student_name": first_record.student_name,
        "class_name": first_record.class_name,
        "lesson_date": lesson_date,
        "start_lesson": start_lesson,
        "consecutive_absences": consecutive_absences,
    }


def _is_excused(reason_code: str, excused_codes: Set[str], count_pending_as_unexcused: bool) -> bool:
    if reason_code in excused_codes:
        return True
    if reason_code == "TECHNICAL_PENDING":
        return not count_pending_as_unexcused
    return False


def build_period_summary(
    records: Sequence[AttendanceRecord],
    run_date: date,
    semester_start: date,
    excused_codes: Set[str],
) -> Dict[str, Dict[str, object]]:
    """Build summary metrics for 7-day, 30-day and semester windows."""

    windows = {
        "week": (run_date - timedelta(days=6), run_date),
        "month": (run_date - timedelta(days=29), run_date),
        "semester": (semester_start, run_date),
    }

    return {
        name: _compute_window_metrics(records, start, end, excused_codes)
        for name, (start, end) in windows.items()
    }


def _compute_window_metrics(
    records: Sequence[AttendanceRecord],
    start: date,
    end: date,
    excused_codes: Set[str],
) -> Dict[str, object]:
    window_rows = [r for r in records if start <= r.lesson_date <= end]
    total_lessons = len(window_rows)
    absent_rows = [r for r in window_rows if r.status == "ABSENT"]
    excused_absent_rows = [r for r in absent_rows if r.reason_code in excused_codes]
    unexcused_absent_rows = [r for r in absent_rows if r.reason_code not in excused_codes]

    students = {r.student_id for r in window_rows}
    students_with_absences = {r.student_id for r in absent_rows}

    absence_rate = (len(absent_rows) / total_lessons) if total_lessons else 0.0
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_students": len(students),
        "students_with_absences": len(students_with_absences),
        "total_lessons": total_lessons,
        "absent_lessons": len(absent_rows),
        "excused_absent_lessons": len(excused_absent_rows),
        "unexcused_absent_lessons": len(unexcused_absent_rows),
        "absence_rate": round(absence_rate, 4),
    }


def build_student_risk_list(
    records: Sequence[AttendanceRecord],
    start: date,
    end: date,
    risk_threshold: float,
) -> List[Dict[str, object]]:
    """Build risk list by absence share in period."""

    grouped: Dict[str, List[AttendanceRecord]] = defaultdict(list)
    for row in records:
        if start <= row.lesson_date <= end:
            grouped[row.student_id].append(row)

    risk_rows: List[Dict[str, object]] = []
    for student_id, rows in grouped.items():
        total = len(rows)
        absences = sum(1 for row in rows if row.status == "ABSENT")
        if total == 0:
            continue
        share = absences / total
        if share >= risk_threshold:
            first = rows[0]
            risk_rows.append(
                {
                    "student_id": student_id,
                    "student_name": first.student_name,
                    "class_name": first.class_name,
                    "total_lessons": total,
                    "absent_lessons": absences,
                    "absence_rate": round(share, 4),
                }
            )

    risk_rows.sort(key=lambda r: (-r["absence_rate"], r["class_name"], r["student_name"]))
    return risk_rows
