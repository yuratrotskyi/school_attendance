import unittest
from pathlib import Path


class TestWindowsLaunchers(unittest.TestCase):
    def test_windows_launchers_exist_and_call_expected_commands(self):
        root = Path(__file__).resolve().parent.parent
        run_daily = root / "windows" / "run-daily.cmd"
        run_ten_day = root / "windows" / "run-attendance-10plus.cmd"

        self.assertTrue(run_daily.exists())
        self.assertTrue(run_ten_day.exists())

        run_daily_text = run_daily.read_text(encoding="utf-8")
        run_ten_day_text = run_ten_day.read_text(encoding="utf-8")

        self.assertIn('pushd "%~dp0.."', run_daily_text)
        self.assertIn('call ".venv\\Scripts\\activate.bat"', run_daily_text)
        self.assertIn("set PYTHONPATH=src", run_daily_text)
        self.assertIn("python -m school_attendance.cli run-daily", run_daily_text)
        self.assertIn("pause", run_daily_text.lower())

        self.assertIn('pushd "%~dp0.."', run_ten_day_text)
        self.assertIn('call ".venv\\Scripts\\activate.bat"', run_ten_day_text)
        self.assertIn("set PYTHONPATH=src", run_ten_day_text)
        self.assertIn("python -m school_attendance.cli run-attendance-10plus", run_ten_day_text)
        self.assertIn("pause", run_ten_day_text.lower())


if __name__ == "__main__":
    unittest.main()
