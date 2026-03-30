import unittest
from unittest.mock import patch

from school_attendance import cli


class TestCliRunAttendance10PlusCommand(unittest.TestCase):
    @patch("builtins.print")
    @patch("school_attendance.cli.run_attendance_10plus")
    @patch("school_attendance.cli.load_config")
    def test_run_attendance_10plus_dispatches_handler(self, mock_load_config, mock_run_attendance_10plus, _mock_print):
        cfg = object()
        mock_load_config.return_value = cfg
        mock_run_attendance_10plus.return_value = {"run_date": "2026-03-30", "paths": {}}

        code = cli.main(
            [
                "run-attendance-10plus",
                "--run-date",
                "2026-03-30",
                "--class",
                "10-А",
                "--class",
                "8-Б",
            ]
        )

        self.assertEqual(0, code)
        kwargs = mock_run_attendance_10plus.call_args.kwargs
        self.assertEqual(cfg, kwargs["config"])
        self.assertEqual(["10-А", "8-Б"], kwargs["include_classes"])


if __name__ == "__main__":
    unittest.main()
