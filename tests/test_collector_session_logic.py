import tempfile
import unittest
from datetime import date
from pathlib import Path

from school_attendance.collector import _build_context_kwargs
from school_attendance.config import AppConfig


class TestCollectorSessionLogic(unittest.TestCase):
    def _config(self, session_state_path: Path) -> AppConfig:
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


if __name__ == "__main__":
    unittest.main()
