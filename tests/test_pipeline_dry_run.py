import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from school_attendance.config import AppConfig
from school_attendance.pipeline import run_daily


class TestPipelineDryRun(unittest.TestCase):
    def test_run_daily_dry_run_from_local_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_file = base / "attendance.csv"
            raw_file.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,7-А,2026-03-04,1,PRESENT,,false\n"
                "123,Іваненко Іван,7-А,2026-03-04,2,ABSENT,UNEXCUSED,false\n"
                "124,Петренко Петро,7-А,2026-03-04,1,ABSENT,EXCUSED_MEDICAL,false\n",
                encoding="utf-8",
            )

            config = AppConfig(
                nz_login=None,
                nz_password=None,
                semester_start=date(2026, 1, 12),
                risk_threshold=0.1,
                excused_codes={"EXCUSED_MEDICAL", "EXCUSED_FAMILY", "EXCUSED_ADMIN"},
                data_dir=base / "data",
                out_dir=base / "out",
                logs_dir=base / "logs",
                selectors_path=None,
                base_url="https://nz.ua",
            )

            result = run_daily(
                config=config,
                run_date=date(2026, 3, 4),
                dry_run=True,
                skip_collect=True,
                raw_files=[raw_file],
            )

            summary_path = Path(result["paths"]["summary_json"])
            detail_path = Path(result["paths"]["detail_csv"])
            report_path = Path(result["paths"]["report_md"])

            self.assertTrue(summary_path.exists())
            self.assertTrue(detail_path.exists())
            self.assertTrue(report_path.exists())
            self.assertEqual(1, result["incident_count"])

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(2, summary["week"]["absent_lessons"])


if __name__ == "__main__":
    unittest.main()
