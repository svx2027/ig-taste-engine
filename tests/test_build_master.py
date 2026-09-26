"""Tests for the pure helpers in build_master.py: safe int coercion (note this
module's as_int defaults to "" on failure, unlike the 0-default version in
build_aggregations.py/taste_profile.py -- both are pinned here so a future
refactor can't quietly unify them onto the wrong default) and the derived
shareability band. Run from the repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import build_master as bm


class AsIntTests(unittest.TestCase):
    def test_numeric_string(self):
        self.assertEqual(bm.as_int("5"), 5)

    def test_empty_string_defaults_empty_string(self):
        self.assertEqual(bm.as_int(""), "")

    def test_none_defaults_empty_string(self):
        self.assertEqual(bm.as_int(None), "")

    def test_non_numeric_defaults_empty_string(self):
        self.assertEqual(bm.as_int("abc"), "")


class ShareabilityTests(unittest.TestCase):
    def test_viral_band(self):
        self.assertEqual(bm.shareability(1000, 150), "viral")

    def test_high_band(self):
        self.assertEqual(bm.shareability(1000, 50), "high")

    def test_mid_band(self):
        self.assertEqual(bm.shareability(1000, 10), "mid")

    def test_low_band(self):
        self.assertEqual(bm.shareability(1000, 5), "low")

    def test_boundary_values_use_strict_inequality(self):
        # 0.1 ratio exactly is NOT > 0.1, so it falls to the "high" band.
        self.assertEqual(bm.shareability(1000, 100), "high")

    def test_zero_likes_returns_empty(self):
        self.assertEqual(bm.shareability(0, 10), "")

    def test_non_numeric_inputs_return_empty(self):
        self.assertEqual(bm.shareability("abc", 10), "")
        self.assertEqual(bm.shareability(None, None), "")


if __name__ == "__main__":
    unittest.main()
