import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from school_attendance.collector import CollectorError, _collect_journal_attendance_records
from school_attendance.config import AppConfig


class _DummyPage:
    pass


class TestCollectorErrorHandling(unittest.TestCase):
    def _config(self) -> AppConfig:
        return AppConfig(
            nz_login=None,
            nz_password=None,
            semester_start=date(2026, 1, 12),
            risk_threshold=0.1,
            excused_codes={"EXCUSED_MEDICAL"},
            data_dir=Path("data"),
            out_dir=Path("out"),
            logs_dir=Path("logs"),
            selectors_path=Path("config/nz_selectors.json"),
            session_state_path=Path("config/nz_session_state.json"),
            base_url="https://nz.ua",
        )

    @patch("school_attendance.collector._collect_single_journal_records")
    @patch("school_attendance.collector._collect_journal_links")
    def test_propagates_collector_error_from_journal_page(self, mock_collect_links, mock_collect_single):
        mock_collect_links.return_value = ["https://nz.ua/journal?id=123"]
        mock_collect_single.side_effect = CollectorError("Cloudflare timeout")

        with self.assertRaises(CollectorError):
            _collect_journal_attendance_records(
                page=_DummyPage(),
                config=self._config(),
                selector_cfg={"journal_list": {}},
            )


if __name__ == "__main__":
    unittest.main()
