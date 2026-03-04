"""Core data models."""

from dataclasses import dataclass
from datetime import date


@dataclass
class AttendanceRecord:
    student_id: str
    student_name: str
    class_name: str
    lesson_date: date
    lesson_no: int
    status: str
    reason_code: str
