import os
import tempfile
import unittest
from pathlib import Path

from school_attendance.config import load_config


class TestConfigSessionPath(unittest.TestCase):
    def setUp(self):
        self._old_session_state_path = os.environ.pop("SESSION_STATE_PATH", None)
        self._old_nz_headless = os.environ.pop("NZ_HEADLESS", None)
        self._old_cf_wait = os.environ.pop("NZ_CLOUDFLARE_WAIT_SECONDS", None)

    def tearDown(self):
        if self._old_session_state_path is not None:
            os.environ["SESSION_STATE_PATH"] = self._old_session_state_path
        else:
            os.environ.pop("SESSION_STATE_PATH", None)
        if self._old_nz_headless is not None:
            os.environ["NZ_HEADLESS"] = self._old_nz_headless
        else:
            os.environ.pop("NZ_HEADLESS", None)
        if self._old_cf_wait is not None:
            os.environ["NZ_CLOUDFLARE_WAIT_SECONDS"] = self._old_cf_wait
        else:
            os.environ.pop("NZ_CLOUDFLARE_WAIT_SECONDS", None)

    def test_load_config_uses_default_session_state_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")

            config = load_config(env_path)

            self.assertEqual(Path("config/nz_session_state.json"), config.session_state_path)

    def test_load_config_uses_custom_session_state_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("SESSION_STATE_PATH=/tmp/custom/session.json\n", encoding="utf-8")

            config = load_config(env_path)

            self.assertEqual(Path("/tmp/custom/session.json"), config.session_state_path)

    def test_load_config_parses_headless_and_cloudflare_wait(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("NZ_HEADLESS=true\nNZ_CLOUDFLARE_WAIT_SECONDS=90\n", encoding="utf-8")

            config = load_config(env_path)

            self.assertTrue(config.nz_headless)
            self.assertEqual(90, config.cloudflare_wait_seconds)


if __name__ == "__main__":
    unittest.main()
