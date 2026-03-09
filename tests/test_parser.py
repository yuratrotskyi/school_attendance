import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from school_attendance.models import AttendanceRecord
from school_attendance.parser import parse_attendance_csv
from school_attendance.reporting import write_report_bundle


class TestParserAndReporting(unittest.TestCase):
    def test_parse_attendance_csv_template_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "attendance.csv"
            csv_path.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,7-А,2026-03-04,2,ABSENT,UNEXCUSED,false\n",
                encoding="utf-8",
            )

            rows = parse_attendance_csv(csv_path)

            self.assertEqual(1, len(rows))
            self.assertEqual("123", rows[0].student_id)
            self.assertEqual(date(2026, 3, 4), rows[0].lesson_date)
            self.assertEqual("ABSENT", rows[0].status)

    def test_parse_attendance_csv_normalizes_class_subgroup_suffix(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "attendance.csv"
            csv_path.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,8-В (ІІ підгрупа),2026-03-04,2,ABSENT,UNEXCUSED,false\n",
                encoding="utf-8",
            )

            rows = parse_attendance_csv(csv_path)

            self.assertEqual(1, len(rows))
            self.assertEqual("8-В", rows[0].class_name)

    def test_write_report_bundle_creates_output_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            records = [
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=2,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 2, 20),
                    lesson_no=3,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 1, 20),
                    lesson_no=1,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="124",
                    student_name="Петренко Петро",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 3),
                    lesson_no=5,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                )
            ]
            summary = {
                "week": {"absent_lessons": 2, "period_start": "2026-02-27", "period_end": "2026-03-04"},
                "month": {"absent_lessons": 3, "period_start": "2026-02-04", "period_end": "2026-03-04"},
                "semester": {"absent_lessons": 4, "period_start": "2026-01-12", "period_end": "2026-03-04"},
            }
            incidents = [
                {
                    "student_id": "123",
                    "student_name": "Іваненко Іван",
                    "class_name": "7-А",
                    "lesson_date": date(2026, 3, 4),
                    "start_lesson": 2,
                    "consecutive_absences": 1,
                }
            ]

            paths = write_report_bundle(
                out_dir=out_dir,
                run_date=date(2026, 3, 4),
                summary=summary,
                records=records,
                incidents=incidents,
            )

            self.assertTrue((out_dir / "summary.json").exists())
            self.assertTrue((out_dir / "detail.csv").exists())
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "student-absence-summary.csv").exists())
            self.assertTrue((out_dir / "відсутність-сьогодні-вчора.csv").exists())
            self.assertEqual(str(out_dir / "report.md"), paths["report_md"])
            self.assertEqual(str(out_dir / "student-absence-summary.csv"), paths["student_absence_summary_csv"])
            self.assertEqual(
                str(out_dir / "відсутність-сьогодні-вчора.csv"),
                paths["class_absence_today_yesterday_csv"],
            )

            loaded_summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(2, loaded_summary["week"]["absent_lessons"])

            with (out_dir / "detail.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(4, len(rows))
            self.assertEqual("123", rows[0]["student_id"])

            with (out_dir / "student-absence-summary.csv").open(encoding="utf-8") as handle:
                grouped_rows = list(csv.DictReader(handle))
            self.assertEqual(2, len(grouped_rows))
            self.assertEqual("123", grouped_rows[0]["ID учня"])
            self.assertEqual("124", grouped_rows[1]["ID учня"])
            self.assertEqual("123", grouped_rows[0]["ID учня"])
            self.assertEqual("1", grouped_rows[0]["Н (7 днів)"])
            self.assertEqual("2", grouped_rows[0]["Н (30 днів)"])
            self.assertEqual("3", grouped_rows[0]["Н"])
            self.assertEqual("1", grouped_rows[1]["Н (7 днів)"])
            self.assertEqual("1", grouped_rows[1]["Н (30 днів)"])
            self.assertEqual("1", grouped_rows[1]["Н"])

            report_text = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("## Пропуски по учнях (Н)", report_text)
            self.assertIn("| Іваненко Іван | 7-А | 1 | 2 | 3 |", report_text)
            self.assertIn("| Петренко Петро | 7-А | 1 | 1 | 1 |", report_text)
            self.assertLess(
                report_text.index("| Іваненко Іван | 7-А | 1 | 2 | 3 |"),
                report_text.index("| Петренко Петро | 7-А | 1 | 1 | 1 |"),
            )

    def test_write_report_bundle_contains_ten_plus_columns_and_optional_periods_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            records = [
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=2,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                )
            ]
            summary = {
                "week": {"absent_lessons": 1, "period_start": "2026-02-27", "period_end": "2026-03-04"},
                "month": {"absent_lessons": 1, "period_start": "2026-02-04", "period_end": "2026-03-04"},
                "semester": {"absent_lessons": 1, "period_start": "2026-01-12", "period_end": "2026-03-04"},
            }
            ten_day_summary = {
                "123": {
                    "ten_plus_periods_count": 2,
                    "last_period_start": "2026-02-01",
                    "last_period_end": "2026-02-11",
                }
            }
            ten_day_periods = [
                {
                    "student_id": "123",
                    "student_name": "Іваненко Іван",
                    "class_name": "7-А",
                    "period_start": "2026-01-12",
                    "period_end": "2026-01-21",
                    "learning_days_absent": 10,
                },
                {
                    "student_id": "123",
                    "student_name": "Іваненко Іван",
                    "class_name": "7-А",
                    "period_start": "2026-02-01",
                    "period_end": "2026-02-11",
                    "learning_days_absent": 11,
                },
            ]

            paths = write_report_bundle(
                out_dir=out_dir,
                run_date=date(2026, 3, 4),
                summary=summary,
                records=records,
                incidents=[],
                ten_day_summary=ten_day_summary,
                ten_day_periods=ten_day_periods,
            )

            with (out_dir / "student-absence-summary.csv").open(encoding="utf-8") as handle:
                grouped_rows = list(csv.DictReader(handle))
            self.assertEqual("2", grouped_rows[0]["К-сть періодів 10+"])
            self.assertEqual("2026-02-01 - 2026-02-11", grouped_rows[0]["Останній період 10+ (від-до)"])

            report_text = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("10+ періодів", report_text)
            self.assertIn("2026-02-01 - 2026-02-11", report_text)

            self.assertIn("ten_day_absence_periods_csv", paths)
            periods_path = out_dir / "ten-day-absence-periods.csv"
            self.assertTrue(periods_path.exists())

    def test_student_absence_summary_headers_are_ukrainian(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            records = [
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=2,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                )
            ]
            summary = {
                "week": {"absent_lessons": 1, "period_start": "2026-02-27", "period_end": "2026-03-04"},
                "month": {"absent_lessons": 1, "period_start": "2026-02-04", "period_end": "2026-03-04"},
                "semester": {"absent_lessons": 1, "period_start": "2026-01-12", "period_end": "2026-03-04"},
            }

            write_report_bundle(
                out_dir=out_dir,
                run_date=date(2026, 3, 4),
                summary=summary,
                records=records,
                incidents=[],
            )

            with (out_dir / "student-absence-summary.csv").open(encoding="utf-8") as handle:
                headers = next(csv.reader(handle))

            self.assertEqual(
                [
                    "ID учня",
                    "Учень",
                    "Клас",
                    "Н (7 днів)",
                    "Н (30 днів)",
                    "Н",
                    "К-сть періодів 10+",
                    "Останній період 10+ (від-до)",
                ],
                headers,
            )

    def test_write_report_bundle_uses_composite_ten_day_key_for_duplicate_student_ids(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            records = [
                AttendanceRecord(
                    student_id="dup",
                    student_name="A",
                    class_name="8-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=1,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="dup",
                    student_name="B",
                    class_name="10-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=1,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
            ]
            summary = {
                "week": {"absent_lessons": 2, "period_start": "2026-02-27", "period_end": "2026-03-04"},
                "month": {"absent_lessons": 2, "period_start": "2026-02-04", "period_end": "2026-03-04"},
                "semester": {"absent_lessons": 2, "period_start": "2026-01-12", "period_end": "2026-03-04"},
            }
            ten_day_summary = {
                "dup::A::8-А": {
                    "ten_plus_periods_count": 1,
                    "last_period_start": "2026-01-12",
                    "last_period_end": "2026-01-21",
                },
                "dup::B::10-А": {
                    "ten_plus_periods_count": 1,
                    "last_period_start": "2026-02-01",
                    "last_period_end": "2026-02-10",
                },
            }

            write_report_bundle(
                out_dir=out_dir,
                run_date=date(2026, 3, 4),
                summary=summary,
                records=records,
                incidents=[],
                ten_day_summary=ten_day_summary,
                ten_day_periods=[],
            )

            with (out_dir / "student-absence-summary.csv").open(encoding="utf-8") as handle:
                grouped_rows = list(csv.DictReader(handle))

            by_name = {row["Учень"]: row for row in grouped_rows}
            self.assertEqual("2026-01-12 - 2026-01-21", by_name["A"]["Останній період 10+ (від-до)"])
            self.assertEqual("2026-02-01 - 2026-02-10", by_name["B"]["Останній період 10+ (від-до)"])

    def test_write_report_bundle_counts_absence_days_not_lessons_in_grouped_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            records = [
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=1,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 3, 4),
                    lesson_no=2,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
                AttendanceRecord(
                    student_id="123",
                    student_name="Іваненко Іван",
                    class_name="7-А",
                    lesson_date=date(2026, 2, 20),
                    lesson_no=1,
                    status="ABSENT",
                    reason_code="UNEXCUSED",
                ),
            ]
            summary = {
                "week": {"absent_lessons": 2, "period_start": "2026-02-27", "period_end": "2026-03-04"},
                "month": {"absent_lessons": 3, "period_start": "2026-02-04", "period_end": "2026-03-04"},
                "semester": {"absent_lessons": 3, "period_start": "2026-01-12", "period_end": "2026-03-04"},
            }

            write_report_bundle(
                out_dir=out_dir,
                run_date=date(2026, 3, 4),
                summary=summary,
                records=records,
                incidents=[],
            )

            with (out_dir / "student-absence-summary.csv").open(encoding="utf-8") as handle:
                grouped_rows = list(csv.DictReader(handle))
            self.assertEqual("1", grouped_rows[0]["Н (7 днів)"])
            self.assertEqual("2", grouped_rows[0]["Н (30 днів)"])
            self.assertEqual("2", grouped_rows[0]["Н"])


if __name__ == "__main__":
    unittest.main()
