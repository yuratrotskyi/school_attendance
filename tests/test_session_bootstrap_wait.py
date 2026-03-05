import unittest

from school_attendance.collector import CollectorError
from school_attendance.session_bootstrap import (
    _open_login_popup_if_needed,
    _wait_for_bootstrap_confirmation,
)


class _FakeLocator:
    def __init__(self, value: int):
        self._value = value

    def count(self):
        return self._value


class _FakePage:
    def __init__(self, selector_counts):
        self._selector_counts = selector_counts
        self.wait_calls = 0

    def locator(self, selector):
        return _FakeLocator(self._selector_counts.get(selector, 0))

    def wait_for_timeout(self, _ms):
        self.wait_calls += 1


class _FakeOpenLoginPage:
    def __init__(self, selector_counts, fail_click=False):
        self._selector_counts = selector_counts
        self.fail_click = fail_click
        self.click_calls = 0
        self.wait_calls = 0

    def locator(self, selector):
        return _FakeLocator(self._selector_counts.get(selector, 0))

    def click(self, _selector):
        self.click_calls += 1
        if self.fail_click:
            raise RuntimeError("click failed")

    def wait_for_timeout(self, _ms):
        self.wait_calls += 1


class TestSessionBootstrapWait(unittest.TestCase):
    def test_returns_selector_when_auth_selector_detected(self):
        page = _FakePage({"a[href*='/account']": 1})

        result = _wait_for_bootstrap_confirmation(
            page=page,
            auth_success_selectors=["a[href*='/account']"],
            timeout_seconds=5,
            manual_enter_detector=lambda: False,
        )

        self.assertEqual("selector", result)
        self.assertEqual(0, page.wait_calls)

    def test_returns_manual_when_enter_detected(self):
        page = _FakePage({"a[href*='/account']": 0})

        result = _wait_for_bootstrap_confirmation(
            page=page,
            auth_success_selectors=["a[href*='/account']"],
            timeout_seconds=5,
            manual_enter_detector=lambda: True,
        )

        self.assertEqual("manual", result)

    def test_raises_timeout_when_no_selector_and_no_manual_confirm(self):
        page = _FakePage({"a[href*='/account']": 0})

        with self.assertRaises(CollectorError):
            _wait_for_bootstrap_confirmation(
                page=page,
                auth_success_selectors=["a[href*='/account']"],
                timeout_seconds=0,
                manual_enter_detector=lambda: False,
            )

    def test_open_login_popup_is_skipped_when_login_form_already_visible(self):
        page = _FakeOpenLoginPage(
            selector_counts={
                "#loginform-login": 1,
            },
            fail_click=True,
        )

        _open_login_popup_if_needed(
            page=page,
            selector_cfg={
                "open_login_button_selector": "text=Увійти",
                "open_login_wait_ms": 1200,
                "login_selector": "#loginform-login",
            },
        )

        self.assertEqual(0, page.click_calls)
        self.assertEqual(0, page.wait_calls)


if __name__ == "__main__":
    unittest.main()
