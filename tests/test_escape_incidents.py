import unittest
from datetime import date

from school_attendance.models import AttendanceRecord
from school_attendance.analytics import detect_escape_incidents


class TestEscapeIncidentDetection(unittest.TestCase):
    def _record(self, lesson_no: int, status: str, reason_code: str = "") -> AttendanceRecord:
        return AttendanceRecord(
            student_id="123",
            student_name="Іваненко Іван",
            class_name="7-А",
            lesson_date=date(2026, 3, 4),
            lesson_no=lesson_no,
            status=status,
            reason_code=reason_code,
        )

    def test_marks_incident_after_first_presence_with_unexcused_absence(self):
        records = [
            self._record(1, "PRESENT"),
            self._record(2, "ABSENT", "UNEXCUSED"),
        ]

        incidents = detect_escape_incidents(records, excused_codes={"EXCUSED_MEDICAL"})

        self.assertEqual(1, len(incidents))
        self.assertEqual(2, incidents[0]["start_lesson"])
        self.assertEqual(1, incidents[0]["consecutive_absences"])

    def test_absent_from_first_lesson_without_presence_is_not_incident(self):
        records = [
            self._record(1, "ABSENT", "UNEXCUSED"),
            self._record(2, "ABSENT", "UNEXCUSED"),
        ]

        incidents = detect_escape_incidents(records, excused_codes={"EXCUSED_MEDICAL"})

        self.assertEqual([], incidents)

    def test_excused_absence_after_presence_is_not_incident(self):
        records = [
            self._record(1, "PRESENT"),
            self._record(2, "ABSENT", "EXCUSED_MEDICAL"),
        ]

        incidents = detect_escape_incidents(records, excused_codes={"EXCUSED_MEDICAL"})

        self.assertEqual([], incidents)

    def test_pending_reason_is_not_incident_by_default(self):
        records = [
            self._record(1, "PRESENT"),
            self._record(2, "ABSENT", "TECHNICAL_PENDING"),
        ]

        incidents = detect_escape_incidents(records, excused_codes={"EXCUSED_MEDICAL"})

        self.assertEqual([], incidents)


if __name__ == "__main__":
    unittest.main()
