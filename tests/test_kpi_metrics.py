import unittest
from datetime import date

from school_attendance.analytics import build_period_summary, build_student_risk_list
from school_attendance.models import AttendanceRecord


class TestKpiMetrics(unittest.TestCase):
    def _record(
        self,
        student_id: str,
        student_name: str,
        lesson_date: date,
        lesson_no: int,
        status: str,
        reason_code: str = "",
        class_name: str = "7-А",
    ) -> AttendanceRecord:
        return AttendanceRecord(
            student_id=student_id,
            student_name=student_name,
            class_name=class_name,
            lesson_date=lesson_date,
            lesson_no=lesson_no,
            status=status,
            reason_code=reason_code,
        )

    def test_build_period_summary_includes_excused_and_unexcused_absences(self):
        run_date = date(2026, 3, 4)
        semester_start = date(2026, 1, 12)
        rows = [
            self._record("1", "A", date(2026, 3, 4), 1, "PRESENT"),
            self._record("1", "A", date(2026, 3, 4), 2, "ABSENT", "UNEXCUSED"),
            self._record("2", "B", date(2026, 3, 4), 1, "ABSENT", "EXCUSED_MEDICAL"),
        ]

        summary = build_period_summary(
            rows,
            run_date=run_date,
            semester_start=semester_start,
            excused_codes={"EXCUSED_MEDICAL", "EXCUSED_FAMILY", "EXCUSED_ADMIN"},
        )

        self.assertEqual(2, summary["week"]["absent_lessons"])
        self.assertEqual(1, summary["week"]["excused_absent_lessons"])
        self.assertEqual(1, summary["week"]["unexcused_absent_lessons"])

    def test_build_student_risk_list_filters_and_sorts_desc(self):
        rows = [
            self._record("1", "A", date(2026, 3, 2), 1, "ABSENT", "UNEXCUSED"),
            self._record("1", "A", date(2026, 3, 2), 2, "ABSENT", "UNEXCUSED"),
            self._record("1", "A", date(2026, 3, 2), 3, "PRESENT"),
            self._record("2", "B", date(2026, 3, 2), 1, "ABSENT", "UNEXCUSED"),
            self._record("2", "B", date(2026, 3, 2), 2, "PRESENT"),
            self._record("3", "C", date(2026, 3, 2), 1, "PRESENT"),
            self._record("3", "C", date(2026, 3, 2), 2, "PRESENT"),
        ]

        risk = build_student_risk_list(
            rows,
            start=date(2026, 3, 1),
            end=date(2026, 3, 7),
            risk_threshold=0.5,
        )

        self.assertEqual(["1", "2"], [row["student_id"] for row in risk])
        self.assertEqual(0.6667, risk[0]["absence_rate"])


if __name__ == "__main__":
    unittest.main()
