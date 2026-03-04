import os
import tempfile
import unittest
from pathlib import Path

from school_attendance.config import load_config


class TestConfigSessionPath(unittest.TestCase):
    def setUp(self):
        self._old_session_state_path = os.environ.pop("SESSION_STATE_PATH", None)

    def tearDown(self):
        if self._old_session_state_path is not None:
            os.environ["SESSION_STATE_PATH"] = self._old_session_state_path
        else:
            os.environ.pop("SESSION_STATE_PATH", None)

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


if __name__ == "__main__":
    unittest.main()
