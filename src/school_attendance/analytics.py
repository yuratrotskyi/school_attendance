"""Attendance analytics and incident detection."""

from collections import defaultdict
from datetime import date, timedelta
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

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


def build_ten_day_absence_periods(
    records: Sequence[AttendanceRecord],
    semester_start: date,
    run_date: date,
    min_learning_days: int = 10,
) -> Tuple[Dict[str, Dict[str, object]], List[Dict[str, object]]]:
    """Build 10+ learning-day absence periods for semester window."""

    learning_days: Dict[Tuple[str, str, str], Dict[date, List[AttendanceRecord]]] = defaultdict(lambda: defaultdict(list))
    student_meta: Dict[Tuple[str, str, str], AttendanceRecord] = {}

    for row in records:
        if row.lesson_date < semester_start or row.lesson_date > run_date:
            continue
        identity = (row.student_id, row.student_name, row.class_name)
        learning_days[identity][row.lesson_date].append(row)
        student_meta.setdefault(identity, row)

    by_student: Dict[str, Dict[str, object]] = {}
    id_alias: Dict[str, Tuple[str, str]] = {}
    periods: List[Dict[str, object]] = []

    for identity, days_map in learning_days.items():
        student_id, student_name, class_name = identity
        ordered_days = sorted(days_map.keys())
        if not ordered_days:
            continue

        current_start: Optional[date] = None
        current_end: Optional[date] = None
        current_length = 0
        student_periods: List[Dict[str, object]] = []
        meta = student_meta[identity]

        for lesson_day in ordered_days:
            rows = days_map[lesson_day]
            is_absent_day = any(item.status == "ABSENT" for item in rows)

            if is_absent_day:
                if current_start is None:
                    current_start = lesson_day
                    current_end = lesson_day
                    current_length = 1
                else:
                    current_end = lesson_day
                    current_length += 1
                continue

            if current_start is not None and current_end is not None and current_length >= min_learning_days:
                student_periods.append(
                    {
                        "student_id": student_id,
                        "student_name": meta.student_name,
                        "class_name": meta.class_name,
                        "period_start": current_start.isoformat(),
                        "period_end": current_end.isoformat(),
                        "learning_days_absent": current_length,
                    }
                )

            current_start = None
            current_end = None
            current_length = 0

        if current_start is not None and current_end is not None and current_length >= min_learning_days:
            student_periods.append(
                {
                    "student_id": student_id,
                    "student_name": meta.student_name,
                    "class_name": meta.class_name,
                    "period_start": current_start.isoformat(),
                    "period_end": current_end.isoformat(),
                    "learning_days_absent": current_length,
                }
            )

        if not student_periods:
            continue

        student_periods.sort(key=lambda item: (item["period_end"], item["period_start"]))
        last_period = student_periods[-1]
        summary_item = {
            "ten_plus_periods_count": len(student_periods),
            "last_period_start": last_period["period_start"],
            "last_period_end": last_period["period_end"],
        }
        composite_key = _student_identity_key(student_id=student_id, student_name=student_name, class_name=class_name)
        by_student[composite_key] = summary_item

        alias_meta = (student_name, class_name)
        if student_id not in id_alias:
            by_student[student_id] = summary_item
            id_alias[student_id] = alias_meta
        elif id_alias[student_id] != alias_meta:
            by_student.pop(student_id, None)
        periods.extend(student_periods)

    periods.sort(key=lambda item: (item["class_name"], item["student_name"], item["period_start"]))
    return by_student, periods


def _student_identity_key(student_id: str, student_name: str, class_name: str) -> str:
    return f"{student_id}::{student_name}::{class_name}"


def build_class_absence_today_yesterday(
    records: Sequence[AttendanceRecord],
    run_date: date,
) -> Dict[str, object]:
    """Build class-level absent-student counts for today and yesterday."""

    yesterday = _previous_school_day(run_date)
    classes: Set[str] = set()
    absent_today: Dict[str, Set[str]] = defaultdict(set)
    absent_yesterday: Dict[str, Set[str]] = defaultdict(set)

    for row in records:
        if row.lesson_date != run_date and row.lesson_date != yesterday:
            continue
        class_name = str(row.class_name or "").strip()
        if not class_name:
            continue
        classes.add(class_name)
        if row.status != "ABSENT":
            continue
        if row.lesson_date == run_date:
            absent_today[class_name].add(row.student_id)
        elif row.lesson_date == yesterday:
            absent_yesterday[class_name].add(row.student_id)

    sorted_classes = sorted(classes, key=_class_sort_key)
    rows: List[Dict[str, object]] = []
    total_today = 0
    total_yesterday = 0
    for class_name in sorted_classes:
        today_count = len(absent_today.get(class_name, set()))
        yesterday_count = len(absent_yesterday.get(class_name, set()))
        total_today += today_count
        total_yesterday += yesterday_count
        rows.append(
            {
                "class_name": class_name,
                "today_count": today_count,
                "yesterday_count": yesterday_count,
            }
        )

    return {
        "total_today": total_today,
        "total_yesterday": total_yesterday,
        "rows": rows,
    }


def _previous_school_day(run_date: date) -> date:
    day = run_date - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def _class_sort_key(class_name: str) -> Tuple[int, int, str, str]:
    normalized = " ".join(str(class_name or "").strip().split())
    match = re.search(r"^\s*(\d{1,2})\s*[-–]\s*([A-Za-zА-Яа-яІіЇїЄєҐґ])", normalized)
    if not match:
        return (1, 0, "", normalized.lower())

    grade = int(match.group(1))
    letter = match.group(2).lower()
    return (0, -grade, letter, normalized.lower())
