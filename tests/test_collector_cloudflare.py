import unittest

from school_attendance.collector import _is_cloudflare_challenge_html, _is_cloudflare_challenge_title


class TestCollectorCloudflareDetection(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
