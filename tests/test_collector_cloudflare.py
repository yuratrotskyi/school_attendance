import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from school_attendance.collector import _ensure_not_cloudflare_blocked, _is_cloudflare_challenge_html, _is_cloudflare_challenge_title
from school_attendance.config import AppConfig


class _FakeChallengePage:
    def __init__(self, states):
        self._states = list(states)
        self._index = 0

    def _is_challenge(self) -> bool:
        if not self._states:
            return False
        return bool(self._states[min(self._index, len(self._states) - 1)])

    def title(self) -> str:
        return "Performing security verification" if self._is_challenge() else "Журнали"

    def content(self) -> str:
        return "verify you are human" if self._is_challenge() else "<html>Журнали</html>"

    def wait_for_timeout(self, _: int) -> None:
        if self._index < len(self._states) - 1:
            self._index += 1


class TestCollectorCloudflareDetection(unittest.TestCase):
    @staticmethod
    def _config() -> AppConfig:
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
            nz_headless=False,
            cloudflare_wait_seconds=10,
            browser_channel="chrome",
        )

    def test_detects_cloudflare_title(self):
        self.assertTrue(_is_cloudflare_challenge_title("Just a moment..."))
        self.assertTrue(_is_cloudflare_challenge_title("Performing security verification"))
        self.assertFalse(_is_cloudflare_challenge_title("Журнали"))

    def test_detects_cloudflare_html_markers(self):
        html = (
            "<html><head><title>Just a moment...</title></head>"
            "<body>Performing security verification"
            "<input type='hidden' id='cf-chl-widget_response' name='cf-turnstile-response'>"
            "</body></html>"
        )
        self.assertTrue(_is_cloudflare_challenge_html(html))
        self.assertFalse(_is_cloudflare_challenge_html("<html><body>Оберіть журнал</body></html>"))

    def test_ignores_regular_journal_page_with_cloudflare_jsd_script(self):
        html = (
            "<html><head><title>Журнали | Нові знання</title></head>"
            "<body><span>Оберіть журнал:</span>"
            "<script>window.__CF$cv$params={r:'x'};"
            "var a=document.createElement('script');"
            "a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';</script>"
            "</body></html>"
        )
        self.assertFalse(_is_cloudflare_challenge_html(html))

    def test_waits_without_notice_when_challenge_resolves_quickly(self):
        page = _FakeChallengePage([True, False])
        cfg = self._config()

        with patch("school_attendance.collector.print") as mocked_print:
            _ensure_not_cloudflare_blocked(
                page=page,
                config=cfg,
                selector_cfg={"cloudflare_wait_seconds": 5, "cloudflare_notice_after_seconds": 3},
                stage="test",
            )

        mocked_print.assert_not_called()

    def test_prints_notice_when_challenge_persists(self):
        page = _FakeChallengePage([True, True, True, True, True, True, False])
        cfg = self._config()

        with patch("school_attendance.collector.print") as mocked_print:
            _ensure_not_cloudflare_blocked(
                page=page,
                config=cfg,
                selector_cfg={"cloudflare_wait_seconds": 6, "cloudflare_notice_after_seconds": 3},
                stage="test",
            )

        self.assertEqual(1, mocked_print.call_count)


if __name__ == "__main__":
    unittest.main()
