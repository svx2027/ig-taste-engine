"""Tests for the pure text-classification helpers in build_combined.py: the
collection-name intent classifier and the hashtag/mention extractors. No CSV
I/O, no network. Run from the repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import build_combined as bc


class ClassifyCollectionTests(unittest.TestCase):
    def test_recreate_keyword(self):
        self.assertEqual(bc.classify_collection("Easy Redo Ideas"), "recreate")

    def test_recreate_keyword_case_insensitive(self):
        self.assertEqual(bc.classify_collection("REMAKE this later"), "recreate")

    def test_negative_keyword(self):
        self.assertEqual(bc.classify_collection("Things that dont work"), "negative")

    def test_negative_keyword_with_apostrophe(self):
        self.assertEqual(bc.classify_collection("Don't do this"), "negative")

    def test_default_is_reference(self):
        self.assertEqual(bc.classify_collection("Blue backdrop test"), "reference")

    def test_empty_string_returns_empty(self):
        self.assertEqual(bc.classify_collection(""), "")

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(bc.classify_collection("   "), "")

    def test_recreate_checked_before_negative(self):
        # "redo" matches RECREATE_KW even though the phrase also reads negatively.
        self.assertEqual(bc.classify_collection("Redo, dont skip"), "recreate")


class ExtractHashtagsTests(unittest.TestCase):
    def test_multiple_hashtags(self):
        self.assertEqual(
            bc.extract_hashtags("Check this out #fun #Recreate2026"),
            "#fun|#Recreate2026")

    def test_none_caption_returns_empty(self):
        self.assertEqual(bc.extract_hashtags(None), "")

    def test_no_hashtags_returns_empty(self):
        self.assertEqual(bc.extract_hashtags("no hashtags here"), "")

    def test_devanagari_hashtag(self):
        self.assertEqual(bc.extract_hashtags("#नमस्ते friends"), "#नमस्ते")


class ExtractMentionsTests(unittest.TestCase):
    def test_multiple_mentions(self):
        self.assertEqual(
            bc.extract_mentions("shoutout to @creator.handle and @another_one"),
            "@creator.handle|@another_one")

    def test_none_caption_returns_empty(self):
        self.assertEqual(bc.extract_mentions(None), "")

    def test_no_mentions_returns_empty(self):
        self.assertEqual(bc.extract_mentions("no mentions"), "")


if __name__ == "__main__":
    unittest.main()
