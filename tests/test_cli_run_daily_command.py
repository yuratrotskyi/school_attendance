import unittest
from unittest.mock import patch

from school_attendance import cli


class TestCliRunDailyCommand(unittest.TestCase):
    @patch("builtins.print")
    @patch("school_attendance.cli.run_daily")
    @patch("school_attendance.cli.load_config")
    def test_run_daily_passes_include_classes(self, mock_load_config, mock_run_daily, _mock_print):
        cfg = object()
        mock_load_config.return_value = cfg
        mock_run_daily.return_value = {"run_date": "2026-03-05", "paths": {}}

        code = cli.main(
            [
                "run-daily",
                "--run-date",
                "2026-03-05",
                "--class",
                "10-А",
                "--class",
                "8-Б",
            ]
        )

        self.assertEqual(0, code)
        kwargs = mock_run_daily.call_args.kwargs
        self.assertEqual(cfg, kwargs["config"])
        self.assertEqual(["10-А", "8-Б"], kwargs["include_classes"])


if __name__ == "__main__":
    unittest.main()
