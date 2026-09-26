"""Tests for the pure aggregation helpers in taste_profile.py: safe int
coercion, top-N counting, and the percentage-formatted summary line each
"## Signature" bullet is built from. Run from the repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import taste_profile as tp


class AsIntTests(unittest.TestCase):
    def test_numeric_string(self):
        self.assertEqual(tp.as_int("42"), 42)

    def test_empty_string_defaults_zero(self):
        self.assertEqual(tp.as_int(""), 0)

    def test_none_defaults_zero(self):
        self.assertEqual(tp.as_int(None), 0)

    def test_non_numeric_defaults_zero(self):
        self.assertEqual(tp.as_int("n/a"), 0)


class TopNTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"format_template": "POV"},
            {"format_template": "POV"},
            {"format_template": "meme"},
            {"format_template": ""},
            {"format_template": None},
        ]

    def test_counts_and_ranks_non_empty_values(self):
        self.assertEqual(tp.topn(self.rows, "format_template"), [("POV", 2), ("meme", 1)])

    def test_ignores_blank_and_missing_values(self):
        # 5 rows in, only 2 distinct non-empty values out.
        result = tp.topn(self.rows, "format_template")
        self.assertEqual(sum(v for _, v in result), 3)

    def test_respects_n_limit(self):
        self.assertEqual(tp.topn(self.rows, "format_template", n=1), [("POV", 2)])


class FmtTests(unittest.TestCase):
    def test_formats_percentages(self):
        self.assertEqual(tp.fmt([("POV", 2), ("meme", 1)], 3), "POV (2, 67%) . meme (1, 33%)")

    def test_zero_total_returns_no_data(self):
        self.assertEqual(tp.fmt([], 0), "(no data)")


class SectionTests(unittest.TestCase):
    def test_builds_full_bullet_line(self):
        rows = [{"x": "A"}, {"x": "A"}, {"x": "B"}]
        self.assertEqual(
            tp.section(rows, "Top X", "x"),
            "- **Top X** -- A (2, 67%) . B (1, 33%)")


if __name__ == "__main__":
    unittest.main()
