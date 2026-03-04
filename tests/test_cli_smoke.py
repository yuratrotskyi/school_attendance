import unittest


class TestCliSmoke(unittest.TestCase):
    def test_can_import_cli(self):
        from school_attendance import cli  # noqa: F401


if __name__ == "__main__":
    unittest.main()
