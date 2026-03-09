import json
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

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
                session_state_path=base / "config" / "nz_session_state.json",
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

    def test_run_daily_cleans_stale_artifacts_for_same_date(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            run_date = date(2026, 3, 4)
            raw_file = base / "attendance.csv"
            raw_file.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,7-А,2026-03-04,1,PRESENT,,false\n",
                encoding="utf-8",
            )

            stale_raw = base / "data" / "raw" / run_date.isoformat() / "stale.csv"
            stale_norm = base / "data" / "normalized" / run_date.isoformat() / "stale.csv"
            stale_proc = base / "data" / "processed" / run_date.isoformat() / "stale.csv"
            stale_out = base / "out" / run_date.isoformat() / "stale.txt"

            stale_raw.parent.mkdir(parents=True, exist_ok=True)
            stale_norm.parent.mkdir(parents=True, exist_ok=True)
            stale_proc.parent.mkdir(parents=True, exist_ok=True)
            stale_out.parent.mkdir(parents=True, exist_ok=True)

            stale_raw.write_text("stale", encoding="utf-8")
            stale_norm.write_text("stale", encoding="utf-8")
            stale_proc.write_text("stale", encoding="utf-8")
            stale_out.write_text("stale", encoding="utf-8")

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
                session_state_path=base / "config" / "nz_session_state.json",
                base_url="https://nz.ua",
            )

            run_daily(
                config=config,
                run_date=run_date,
                dry_run=True,
                skip_collect=True,
                raw_files=[raw_file],
            )

            self.assertFalse(stale_raw.exists())
            self.assertFalse(stale_norm.exists())
            self.assertFalse(stale_proc.exists())
            self.assertFalse(stale_out.exists())

    def test_run_daily_writes_ten_day_periods_csv_when_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_file = base / "attendance.csv"
            lines = ["student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident"]
            for day in range(12, 22):
                lines.append(f"123,Іваненко Іван,7-А,2026-01-{day:02d},1,ABSENT,UNEXCUSED,false")
            raw_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
                session_state_path=base / "config" / "nz_session_state.json",
                base_url="https://nz.ua",
            )

            result = run_daily(
                config=config,
                run_date=date(2026, 1, 21),
                dry_run=True,
                skip_collect=True,
                raw_files=[raw_file],
            )

            self.assertIn("ten_day_absence_periods_csv", result["paths"])
            periods_path = Path(result["paths"]["ten_day_absence_periods_csv"])
            self.assertTrue(periods_path.exists())

    def test_run_daily_skips_ten_day_periods_csv_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_file = base / "attendance.csv"
            lines = ["student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident"]
            for day in range(12, 21):
                lines.append(f"123,Іваненко Іван,7-А,2026-01-{day:02d},1,ABSENT,UNEXCUSED,false")
            raw_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

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
                session_state_path=base / "config" / "nz_session_state.json",
                base_url="https://nz.ua",
            )

            result = run_daily(
                config=config,
                run_date=date(2026, 1, 20),
                dry_run=True,
                skip_collect=True,
                raw_files=[raw_file],
            )

            self.assertNotIn("ten_day_absence_periods_csv", result["paths"])

    def test_run_daily_writes_ukrainian_class_daily_absence_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_file = base / "attendance.csv"
            raw_file.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,11-А,2026-03-05,1,ABSENT,UNEXCUSED,false\n"
                "123,Іваненко Іван,11-А,2026-03-05,2,ABSENT,UNEXCUSED,false\n"
                "124,Петренко Петро,11-Б,2026-03-05,1,PRESENT,,false\n"
                "124,Петренко Петро,11-Б,2026-03-04,1,ABSENT,UNEXCUSED,false\n"
                "125,Сидоренко Сидір,10-А,2026-03-04,1,ABSENT,UNEXCUSED,false\n",
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
                session_state_path=base / "config" / "nz_session_state.json",
                base_url="https://nz.ua",
            )

            result = run_daily(
                config=config,
                run_date=date(2026, 3, 5),
                dry_run=True,
                skip_collect=True,
                raw_files=[raw_file],
            )

            self.assertIn("class_absence_today_yesterday_csv", result["paths"])
            path = Path(result["paths"]["class_absence_today_yesterday_csv"])
            self.assertTrue(path.exists())
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(["клас", "к-сть сьогодні", "к-сть вчора"], rows[0])
            self.assertEqual(["усього", "1", "2"], rows[1])

    @patch("school_attendance.pipeline.collect_raw_exports")
    def test_run_daily_passes_include_classes_to_collection(self, mock_collect_raw_exports):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_file = base / "attendance.csv"
            raw_file.write_text(
                "student_id,student_name,class,date,lesson_no,status,reason_code,is_escape_incident\n"
                "123,Іваненко Іван,10-А,2026-03-05,1,PRESENT,,false\n",
                encoding="utf-8",
            )
            mock_collect_raw_exports.return_value = [raw_file]

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
                session_state_path=base / "config" / "nz_session_state.json",
                base_url="https://nz.ua",
            )

            run_date = date(2026, 3, 5)
            run_daily(
                config=config,
                run_date=run_date,
                dry_run=False,
                skip_collect=False,
                include_classes=["10-А", "8-Б"],
            )

            mock_collect_raw_exports.assert_called_once_with(
                config,
                run_date,
                include_classes=["10-А", "8-Б"],
            )


if __name__ == "__main__":
    unittest.main()
