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
                )
            ]
            summary = {"week": {"absent_lessons": 1}}
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
            self.assertEqual(str(out_dir / "report.md"), paths["report_md"])

            loaded_summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, loaded_summary["week"]["absent_lessons"])

            with (out_dir / "detail.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(rows))
            self.assertEqual("123", rows[0]["student_id"])


if __name__ == "__main__":
    unittest.main()
