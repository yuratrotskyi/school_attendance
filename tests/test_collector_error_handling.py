import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from school_attendance.collector import (
    CollectorError,
    _collect_journal_attendance_records,
    _collect_journal_records_parallel,
    _split_journal_urls_for_workers,
)
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

    @patch("school_attendance.collector._collect_journal_records_parallel")
    @patch("school_attendance.collector._collect_journal_records_sequential")
    @patch("school_attendance.collector._collect_journal_links")
    def test_uses_parallel_collection_when_workers_gt_one(
        self,
        mock_collect_links,
        mock_collect_sequential,
        mock_collect_parallel,
    ):
        mock_collect_links.return_value = ["https://nz.ua/journal?id=123"]
        mock_collect_parallel.return_value = []
        mock_collect_sequential.return_value = []

        _collect_journal_attendance_records(
            page=_DummyPage(),
            config=self._config(),
            selector_cfg={"journal_list": {"workers": 2}},
        )

        mock_collect_parallel.assert_called_once()
        mock_collect_sequential.assert_not_called()

    @patch("school_attendance.collector._collect_journal_records_parallel")
    @patch("school_attendance.collector._collect_journal_records_sequential")
    @patch("school_attendance.collector._collect_journal_links")
    def test_uses_sequential_collection_when_workers_eq_one(
        self,
        mock_collect_links,
        mock_collect_sequential,
        mock_collect_parallel,
    ):
        mock_collect_links.return_value = ["https://nz.ua/journal?id=123"]
        mock_collect_parallel.return_value = []
        mock_collect_sequential.return_value = []

        _collect_journal_attendance_records(
            page=_DummyPage(),
            config=self._config(),
            selector_cfg={"journal_list": {"workers": 1}},
        )

        mock_collect_sequential.assert_called_once()
        mock_collect_parallel.assert_not_called()

    def test_split_journal_urls_for_workers_balances_round_robin(self):
        urls = ["u1", "u2", "u3", "u4", "u5"]
        got = _split_journal_urls_for_workers(urls, workers=2)
        self.assertEqual([["u1", "u3", "u5"], ["u2", "u4"]], got)

    @patch("school_attendance.collector._collect_journal_batch_with_worker")
    def test_parallel_collection_dispatches_batches_instead_of_per_url(self, mock_collect_batch):
        urls = ["u1", "u2", "u3", "u4", "u5"]
        mock_collect_batch.side_effect = lambda batch, *_: [{"url": item} for item in batch]

        rows = _collect_journal_records_parallel(
            journal_urls=urls,
            workers=2,
            config=self._config(),
            selector_cfg={"journal_page": {}},
        )

        self.assertEqual(2, mock_collect_batch.call_count)
        called_batches = [tuple(call.args[0]) for call in mock_collect_batch.call_args_list]
        self.assertCountEqual([("u1", "u3", "u5"), ("u2", "u4")], called_batches)
        self.assertEqual(5, len(rows))

    @patch("school_attendance.collector._collect_journal_batch_with_worker")
    @patch("school_attendance.collector._collect_journal_batch_on_page")
    def test_parallel_collection_uses_current_page_as_one_worker(
        self,
        mock_collect_on_page,
        mock_collect_batch,
    ):
        urls = ["u1", "u2", "u3", "u4", "u5"]
        mock_collect_on_page.side_effect = lambda *args, **kwargs: [
            {"url": item} for item in kwargs["journal_urls"]
        ]
        mock_collect_batch.side_effect = lambda batch, *_args: [{"url": item} for item in batch]

        rows = _collect_journal_records_parallel(
            journal_urls=urls,
            workers=2,
            config=self._config(),
            selector_cfg={"journal_page": {}},
            page=_DummyPage(),
        )

        mock_collect_on_page.assert_called_once()
        on_page_batch = tuple(mock_collect_on_page.call_args.kwargs["journal_urls"])
        worker_batch = tuple(mock_collect_batch.call_args.args[0])
        self.assertEqual(("u1", "u3", "u5"), on_page_batch)
        self.assertEqual(("u2", "u4"), worker_batch)
        self.assertEqual(1, mock_collect_batch.call_count)
        self.assertEqual(5, len(rows))


if __name__ == "__main__":
    unittest.main()
