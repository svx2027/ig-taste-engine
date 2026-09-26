"""Tests for the pure helpers in build_aggregations.py: safe int coercion and
the collections-list parser shared by the audio-library and creator-leaderboard
builders. Run from the repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import build_aggregations as ba


class AsIntTests(unittest.TestCase):
    def test_numeric_string(self):
        self.assertEqual(ba.as_int("5"), 5)

    def test_int_passthrough(self):
        self.assertEqual(ba.as_int(3), 3)

    def test_empty_string_defaults_zero(self):
        self.assertEqual(ba.as_int(""), 0)

    def test_none_defaults_zero(self):
        self.assertEqual(ba.as_int(None), 0)

    def test_non_numeric_string_defaults_zero(self):
        self.assertEqual(ba.as_int("abc"), 0)


class CollectionsOfTests(unittest.TestCase):
    def test_splits_and_strips_pipe_separated_collections(self):
        row = {"collections": "A|B| C "}
        self.assertEqual(ba.collections_of(row), ["A", "B", "C"])

    def test_falls_back_to_singular_collection_key(self):
        row = {"collection": "Solo"}
        self.assertEqual(ba.collections_of(row), ["Solo"])

    def test_empty_collections_falls_back_to_singular(self):
        row = {"collections": "", "collection": "Fallback"}
        self.assertEqual(ba.collections_of(row), ["Fallback"])

    def test_missing_both_keys_returns_empty_list(self):
        self.assertEqual(ba.collections_of({}), [])


if __name__ == "__main__":
    unittest.main()
