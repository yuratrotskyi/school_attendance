import unittest

from school_attendance.collector import CollectorError
from school_attendance.session_bootstrap import _wait_for_bootstrap_confirmation


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


if __name__ == "__main__":
    unittest.main()
