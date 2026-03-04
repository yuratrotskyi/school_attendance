import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Optional

from school_attendance.collector import _build_context_kwargs, _build_launch_kwargs
from school_attendance.config import AppConfig


class TestCollectorSessionLogic(unittest.TestCase):
    def _config(
        self,
        session_state_path: Path,
        nz_headless: bool = False,
        browser_channel: Optional[str] = "chrome",
    ) -> AppConfig:
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
            session_state_path=session_state_path,
            base_url="https://nz.ua",
            nz_headless=nz_headless,
            cloudflare_wait_seconds=180,
            browser_channel=browser_channel,
        )

    def test_build_context_kwargs_without_saved_session(self):
        cfg = self._config(Path("/tmp/non-existing-session-state.json"))

        kwargs = _build_context_kwargs(cfg)

        self.assertEqual({"accept_downloads": True}, kwargs)

    def test_build_context_kwargs_with_saved_session(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_path = Path(tmp_dir) / "session.json"
            session_path.write_text("{}", encoding="utf-8")
            cfg = self._config(session_path)

            kwargs = _build_context_kwargs(cfg)

            self.assertEqual(True, kwargs["accept_downloads"])
            self.assertEqual(str(session_path), kwargs["storage_state"])

    def test_build_launch_kwargs_headful_with_chrome_channel(self):
        cfg = self._config(Path("/tmp/non-existing-session-state.json"))

        kwargs = _build_launch_kwargs(cfg)

        self.assertEqual(False, kwargs["headless"])
        self.assertEqual("chrome", kwargs["channel"])
        self.assertIn("--disable-blink-features=AutomationControlled", kwargs["args"])

    def test_build_launch_kwargs_headless_without_channel(self):
        cfg = self._config(
            Path("/tmp/non-existing-session-state.json"),
            nz_headless=True,
            browser_channel=None,
        )

        kwargs = _build_launch_kwargs(cfg)

        self.assertEqual(True, kwargs["headless"])
        self.assertNotIn("channel", kwargs)


if __name__ == "__main__":
    unittest.main()
