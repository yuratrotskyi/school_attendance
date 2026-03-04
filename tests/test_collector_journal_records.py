import tempfile
import unittest
from pathlib import Path

from school_attendance.collector import (
    _collect_paginated_links,
    _extract_candidate_journal_hrefs,
    _is_journal_href,
    _normalize_journal_rows,
    _write_journal_records_csv,
)


class TestCollectorJournalRecords(unittest.TestCase):
    def test_map_mark_n_as_absent_and_hv_as_ignored(self):
        rows = [
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 1,
                "mark": "",
            },
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 2,
                "mark": "Н",
            },
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 3,
                "mark": "ХВ",
            },
        ]

        got = _normalize_journal_rows(rows, journal_id="j-1")

        self.assertEqual(2, len(got))
        self.assertEqual("PRESENT", got[0]["status"])
        self.assertEqual("ABSENT", got[1]["status"])
        self.assertEqual(2, got[1]["lesson_no"])

    def test_deduplicates_by_journal_student_date_lesson(self):
        rows = [
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 2,
                "mark": "Н",
            },
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 2,
                "mark": "Н",
            },
        ]

        got = _normalize_journal_rows(rows, journal_id="journal-42")

        self.assertEqual(1, len(got))
        self.assertEqual("ABSENT", got[0]["status"])

    def test_collect_paginated_links_merges_pages_and_deduplicates(self):
        pages = [
            {
                "links": ["/journal/1", "https://nz.ua/journal/2"],
                "next": "/journal/list?page=2",
            },
            {
                "links": ["/journal/2", "/journal/3"],
                "next": None,
            },
        ]

        got = _collect_paginated_links(pages, base_url="https://nz.ua")

        self.assertEqual(
            [
                "https://nz.ua/journal/1",
                "https://nz.ua/journal/2",
                "https://nz.ua/journal/3",
            ],
            got,
        )

    def test_recognizes_journal_links_with_query_id_format(self):
        self.assertTrue(_is_journal_href("/journal?id=123"))
        self.assertTrue(_is_journal_href("journal?id=123"))
        self.assertTrue(_is_journal_href("https://nz.ua/journal?id=777"))
        self.assertTrue(_is_journal_href("/journal/entry/42"))
        self.assertFalse(_is_journal_href("/journal/list"))
        self.assertFalse(_is_journal_href("https://nz.ua/account/profile"))

    def test_extract_candidate_journal_hrefs_from_js_and_html_values(self):
        raw_values = [
            "window.location='journal?id=321'",
            "openJournal('/journal?id=456')",
            "<a href=\"https://nz.ua/journal/list?page=2\">next</a>",
            "data-url=\"https://nz.ua/journal/987\"",
            "href=\"/account/profile\"",
        ]

        got = _extract_candidate_journal_hrefs(raw_values)

        self.assertIn("journal?id=321", got)
        self.assertIn("/journal?id=456", got)
        self.assertIn("https://nz.ua/journal/987", got)
        self.assertNotIn("https://nz.ua/journal/list?page=2", got)

    def test_write_raw_csv_from_normalized_records(self):
        records = [
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "7-А",
                "date": "2026-03-04",
                "lesson_no": 2,
                "status": "ABSENT",
                "reason_code": "",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir)
            csv_path = _write_journal_records_csv(run_dir, records)

            self.assertTrue(csv_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("student_id,student_name,class,date,lesson_no,status,reason_code", content)
            self.assertIn("1,Іваненко Іван,7-А,2026-03-04,2,ABSENT,", content)


if __name__ == "__main__":
    unittest.main()
