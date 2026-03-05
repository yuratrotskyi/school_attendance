import tempfile
import unittest
from pathlib import Path

from school_attendance.collector import (
    _build_grid_column_meta,
    _collect_paginated_links,
    _extract_class_name_hint,
    _extract_dates_from_topics,
    _extract_candidate_journal_hrefs,
    _is_journal_href,
    _looks_like_class_chip_label,
    _normalize_journal_rows,
    _pick_first_pagination_href,
    _pick_next_pagination_href,
    _resolve_date_from_day_and_month,
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

    def test_collect_paginated_links_filters_non_journal_actions_and_amp_duplicates(self):
        pages = [
            {
                "links": [
                    "/journal/index?journal=13190998&subgroup=2261045",
                    "/journal/index?journal=13190998&amp;subgroup=2261045",
                    "/journal/create",
                    "/journal/edit?journal_id=13190998",
                    "/journal/export-xls?journal=13190998",
                ],
                "next": None,
            }
        ]

        got = _collect_paginated_links(pages, base_url="https://nz.ua")

        self.assertEqual(["https://nz.ua/journal/index?journal=13190998&subgroup=2261045"], got)

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

    def test_detects_class_chip_label(self):
        self.assertTrue(_looks_like_class_chip_label("5-А(I група)"))
        self.assertTrue(_looks_like_class_chip_label("10-Б"))
        self.assertTrue(_looks_like_class_chip_label("7-A"))
        self.assertFalse(_looks_like_class_chip_label("Оберіть журнал"))
        self.assertFalse(_looks_like_class_chip_label("Зведені звіти"))

    def test_resolve_date_from_day_and_month_for_cross_year_semester(self):
        semester = ("2025-09-01", "2026-06-05")

        jan_date = _resolve_date_from_day_and_month("12", "Січ.", semester)
        nov_date = _resolve_date_from_day_and_month("16", "Лист.", semester)

        self.assertEqual("2026-01-12", jan_date)
        self.assertEqual("2025-11-16", nov_date)

    def test_extract_dates_from_topics_parses_ukrainian_months(self):
        topics = [
            {"date_text": "12 січня", "lesson_no": "16"},
            {"date_text": "19 лютого", "lesson_no": "20"},
        ]

        got = _extract_dates_from_topics(topics, ("2025-09-01", "2026-06-05"))

        self.assertEqual(
            [
                {"date": "2026-01-12", "lesson_no": 16},
                {"date": "2026-02-19", "lesson_no": 20},
            ],
            got,
        )

    def test_build_grid_column_meta_handles_day_cells_with_month_text(self):
        day_headers = [
            "#",
            "ПІБ учня",
            "23 Бер.",
            "24",
            "30",
            "31",
            "6 Квіт.",
            "7",
            "13",
            "14",
        ]
        month_headers = [{"text": token, "span": 1} for token in day_headers]

        got = _build_grid_column_meta(
            day_headers=day_headers,
            month_headers=month_headers,
            semester_bounds=("2026-01-07", "2026-06-05"),
            topics_dates=[],
        )

        self.assertEqual(
            [
                "2026-03-23",
                "2026-03-24",
                "2026-03-30",
                "2026-03-31",
                "2026-04-06",
                "2026-04-07",
                "2026-04-13",
                "2026-04-14",
            ],
            [item["date"] for item in got],
        )

    def test_pick_next_pagination_href_prefers_new_page(self):
        current = "https://nz.ua/journal?id=123&page=1"
        links = [
            "https://nz.ua/journal?id=123&page=1",
            "/journal?id=123&page=2",
            "/journal?id=123&page=3",
        ]

        next_href = _pick_next_pagination_href(current_url=current, hrefs=links, base_url="https://nz.ua")

        self.assertEqual("https://nz.ua/journal?id=123&page=2", next_href)

    def test_pick_first_pagination_href_moves_to_page_one_from_middle(self):
        current = "https://nz.ua/journal?id=123&page=5"
        links = [
            "https://nz.ua/journal?id=123&page=4",
            "https://nz.ua/journal?id=123&page=1",
            "https://nz.ua/journal?id=123&page=5",
            "https://nz.ua/journal?id=123&page=6",
        ]

        first_href = _pick_first_pagination_href(current_url=current, hrefs=links, base_url="https://nz.ua")

        self.assertEqual("https://nz.ua/journal?id=123&page=1", first_href)

    def test_extract_class_name_hint_from_title_and_header_text(self):
        from_title = _extract_class_name_hint("Журнал 6-А (І група підгрупа) | Нові знання")
        from_header = _extract_class_name_hint("Журнал оцінок для 5-А (I група підгрупа) [Інформатика]")

        self.assertEqual("6-А", from_title)
        self.assertEqual("5-А", from_header)

    def test_normalize_journal_rows_normalizes_class_name(self):
        rows = [
            {
                "student_id": "1",
                "student_name": "Іваненко Іван",
                "class_name": "8-В (ІІ підгрупа)",
                "date": "2026-03-04",
                "lesson_no": 2,
                "mark": "Н",
            }
        ]

        got = _normalize_journal_rows(rows, journal_id="j-1")

        self.assertEqual(1, len(got))
        self.assertEqual("8-В", got[0]["class_name"])

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
