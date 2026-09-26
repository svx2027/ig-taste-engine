"""Tests for the djb2 signature used by verify_feed.py to prove the
shortcodes on disk exactly match what the browser-side capture read (catching
any transcription error in the browser -> context -> disk hop). Run from the
repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import verify_feed as vf


class Djb2Tests(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(vf.djb2(""), 5381)

    def test_single_char(self):
        self.assertEqual(vf.djb2("a"), 177604)

    def test_known_value(self):
        self.assertEqual(vf.djb2("abc"), 193409669)

    def test_order_sensitive(self):
        self.assertNotEqual(vf.djb2("abc"), vf.djb2("acb"))

    def test_deterministic(self):
        self.assertEqual(vf.djb2("ABC123,DEF456"), vf.djb2("ABC123,DEF456"))

    def test_result_is_32_bit(self):
        result = vf.djb2("some fairly long shortcode list joined by commas" * 5)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 2 ** 32)


if __name__ == "__main__":
    unittest.main()
