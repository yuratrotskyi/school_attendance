import unittest
from datetime import date

from school_attendance.analytics import (
    build_class_absence_today_yesterday,
    build_period_summary,
    build_student_risk_list,
    build_ten_day_absence_periods,
)
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

    def test_build_ten_day_absence_periods_returns_multiple_periods(self):
        rows = []
        for day in range(12, 22):
            rows.append(self._record("s1", "Student One", date(2026, 1, day), 1, "ABSENT"))
        rows.append(self._record("s1", "Student One", date(2026, 1, 22), 1, "PRESENT"))
        for day in range(1, 12):
            rows.append(self._record("s1", "Student One", date(2026, 2, day), 1, "ABSENT"))

        for day in range(1, 10):
            rows.append(self._record("s2", "Student Two", date(2026, 2, day), 1, "ABSENT"))
        rows.append(self._record("s2", "Student Two", date(2026, 2, 10), 1, "PRESENT"))

        student_summary, periods = build_ten_day_absence_periods(
            records=rows,
            semester_start=date(2026, 1, 12),
            run_date=date(2026, 3, 4),
            min_learning_days=10,
        )

        self.assertEqual(2, student_summary["s1"]["ten_plus_periods_count"])
        self.assertEqual("2026-02-01", student_summary["s1"]["last_period_start"])
        self.assertEqual("2026-02-11", student_summary["s1"]["last_period_end"])
        self.assertNotIn("s2", student_summary)

        s1_periods = [item for item in periods if item["student_id"] == "s1"]
        self.assertEqual(2, len(s1_periods))
        self.assertEqual(10, s1_periods[0]["learning_days_absent"])
        self.assertEqual(11, s1_periods[1]["learning_days_absent"])

    def test_build_class_absence_today_yesterday_counts_and_sorting(self):
        run_date = date(2026, 3, 5)
        rows = [
            self._record("1", "A", date(2026, 3, 5), 1, "ABSENT", class_name="11-А"),
            self._record("1", "A", date(2026, 3, 5), 2, "ABSENT", class_name="11-А"),
            self._record("2", "B", date(2026, 3, 5), 1, "PRESENT", class_name="11-А"),
            self._record("1", "A", date(2026, 3, 4), 1, "ABSENT", class_name="11-А"),
            self._record("3", "C", date(2026, 3, 5), 1, "ABSENT", class_name="11-Б"),
            self._record("4", "D", date(2026, 3, 4), 1, "PRESENT", class_name="11-Б"),
            self._record("5", "E", date(2026, 3, 5), 1, "PRESENT", class_name="10-А"),
            self._record("5", "E", date(2026, 3, 4), 1, "ABSENT", class_name="10-А"),
        ]

        got = build_class_absence_today_yesterday(rows, run_date=run_date)

        self.assertEqual(2, got["total_today"])
        self.assertEqual(2, got["total_yesterday"])
        self.assertEqual(["11-А", "11-Б", "10-А"], [row["class_name"] for row in got["rows"]])
        self.assertEqual(1, got["rows"][0]["today_count"])
        self.assertEqual(1, got["rows"][0]["yesterday_count"])
        self.assertEqual(1, got["rows"][1]["today_count"])
        self.assertEqual(0, got["rows"][1]["yesterday_count"])
        self.assertEqual(0, got["rows"][2]["today_count"])
        self.assertEqual(1, got["rows"][2]["yesterday_count"])

    def test_build_class_absence_today_yesterday_uses_friday_for_monday_run(self):
        run_date = date(2026, 3, 9)
        rows = [
            self._record("1", "A", date(2026, 3, 9), 1, "ABSENT", class_name="11-А"),
            self._record("2", "B", date(2026, 3, 7), 1, "ABSENT", class_name="11-А"),
            self._record("3", "C", date(2026, 3, 6), 1, "ABSENT", class_name="10-А"),
        ]

        got = build_class_absence_today_yesterday(rows, run_date=run_date)

        self.assertEqual(1, got["total_today"])
        self.assertEqual(1, got["total_yesterday"])
        by_class = {row["class_name"]: row for row in got["rows"]}
        self.assertEqual(0, by_class["11-А"]["yesterday_count"])
        self.assertEqual(1, by_class["10-А"]["yesterday_count"])

    def test_build_ten_day_absence_periods_separates_duplicate_student_ids(self):
        rows = []
        for day in range(12, 22):
            rows.append(self._record("dup", "A", date(2026, 1, day), 1, "ABSENT", class_name="8-А"))
            rows.append(self._record("dup", "B", date(2026, 1, day), 1, "PRESENT", class_name="10-А"))
        rows.append(self._record("dup", "A", date(2026, 1, 22), 1, "PRESENT", class_name="8-А"))
        for day in range(1, 11):
            rows.append(self._record("dup", "A", date(2026, 2, day), 1, "PRESENT", class_name="8-А"))
            rows.append(self._record("dup", "B", date(2026, 2, day), 1, "ABSENT", class_name="10-А"))
        rows.append(self._record("dup", "B", date(2026, 2, 11), 1, "PRESENT", class_name="10-А"))

        student_summary, periods = build_ten_day_absence_periods(
            records=rows,
            semester_start=date(2026, 1, 12),
            run_date=date(2026, 3, 4),
            min_learning_days=10,
        )

        self.assertIn("dup::A::8-А", student_summary)
        self.assertIn("dup::B::10-А", student_summary)
        self.assertNotIn("dup", student_summary)
        self.assertEqual({"A", "B"}, {item["student_name"] for item in periods})
        self.assertEqual({"8-А", "10-А"}, {item["class_name"] for item in periods})


if __name__ == "__main__":
    unittest.main()
