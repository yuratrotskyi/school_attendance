import unittest
from pathlib import Path


class TestWindowsLaunchers(unittest.TestCase):
    def test_windows_launchers_exist_and_call_expected_commands(self):
        root = Path(__file__).resolve().parent.parent
        first_setup = root / "windows" / "first-setup.cmd"
        run_daily = root / "windows" / "run-daily.cmd"
        run_ten_day = root / "windows" / "run-attendance-10plus.cmd"

        self.assertTrue(first_setup.exists())
        self.assertTrue(run_daily.exists())
        self.assertTrue(run_ten_day.exists())

        first_setup_text = first_setup.read_text(encoding="utf-8")
        run_daily_text = run_daily.read_text(encoding="utf-8")
        run_ten_day_text = run_ten_day.read_text(encoding="utf-8")

        self.assertIn('pushd "%~dp0.."', first_setup_text)
        self.assertIn("py -3 -m venv .venv", first_setup_text)
        self.assertIn('call ".venv\\Scripts\\activate.bat"', first_setup_text)
        self.assertIn("pip install -r requirements.txt", first_setup_text)
        self.assertIn("python -m playwright install chromium", first_setup_text)
        self.assertIn('copy ".env.example" ".env"', first_setup_text.lower())
        self.assertIn('copy "config\\nz_selectors.example.json" "config\\nz_selectors.json"', first_setup_text.lower())
        self.assertIn("python -m school_attendance.cli bootstrap-session --timeout-seconds 300", first_setup_text)
        self.assertIn("pause", first_setup_text.lower())

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
