import unittest
from pathlib import Path
from unittest.mock import patch

from school_attendance import cli


class TestCliBootstrapCommand(unittest.TestCase):
    @patch("builtins.print")
    @patch("school_attendance.cli.bootstrap_session")
    @patch("school_attendance.cli.load_config")
    def test_bootstrap_command_dispatches_handler(self, mock_load_config, mock_bootstrap_session, _mock_print):
        cfg = object()
        mock_load_config.return_value = cfg
        mock_bootstrap_session.return_value = Path("config/nz_session_state.json")

        code = cli.main(["bootstrap-session", "--env-file", ".env", "--timeout-seconds", "30"])

        self.assertEqual(0, code)
        mock_load_config.assert_called_once_with(Path(".env"))
        mock_bootstrap_session.assert_called_once_with(config=cfg, timeout_seconds=30)


if __name__ == "__main__":
    unittest.main()
