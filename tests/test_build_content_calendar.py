"""Tests for the deterministic scheduling core of build_content_calendar.py:
the violation counter and the greedy-plus-hill-climb sequencer that spaces
named audio picks 3 days apart and never runs the same format 3 days
straight. No file I/O -- md_ideas/md_calendar/write_csv aren't covered here.
Run from the repo root:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest

import build_content_calendar as cal


def concept(title, fmt, audio_pick=""):
    return {"title": title, "format": fmt, "audio_pick": audio_pick, "composite": 0}


class TotalViolationsTests(unittest.TestCase):
    def test_three_same_format_in_a_row_is_one_violation(self):
        order = [concept("a", "A"), concept("b", "A"), concept("c", "A")]
        self.assertEqual(cal.total_violations(order), 1)

    def test_two_same_format_in_a_row_is_no_violation(self):
        order = [concept("a", "A"), concept("b", "A"), concept("c", "B")]
        self.assertEqual(cal.total_violations(order), 0)

    def test_repeated_named_audio_within_3_days_is_a_violation(self):
        order = [
            concept("a", "A", "Song X"),
            concept("b", "B", "Other"),
            concept("c", "C", "Song X"),
        ]
        self.assertEqual(cal.total_violations(order), 1)

    def test_exempt_audio_never_counts_even_when_repeated(self):
        order = [
            concept("a", "A", "instrumental"),
            concept("b", "B", "instrumental"),
            concept("c", "C", "instrumental"),
        ]
        self.assertEqual(cal.total_violations(order), 0)

    def test_blank_audio_is_exempt(self):
        order = [concept("a", "A", ""), concept("b", "B", ""), concept("c", "C", "")]
        self.assertEqual(cal.total_violations(order), 0)

    def test_audio_repeat_outside_3_day_window_does_not_count(self):
        order = [
            concept("a", "A", "Song X"),
            concept("b", "B", "y"),
            concept("c", "C", "z"),
            concept("d", "D", "w"),
            concept("e", "E", "Song X"),
        ]
        # "Song X" reappears at index 4; the lookback window is order[1:4],
        # which does not include index 0, so this must not be flagged.
        self.assertEqual(cal.total_violations(order), 0)


class SequenceTests(unittest.TestCase):
    def test_preserves_every_concept_exactly_once(self):
        concepts = [
            {"title": "c1", "format": "A", "composite": 10, "audio_pick": "song1"},
            {"title": "c2", "format": "A", "composite": 9, "audio_pick": ""},
            {"title": "c3", "format": "B", "composite": 8, "audio_pick": "song1"},
            {"title": "c4", "format": "A", "composite": 7, "audio_pick": ""},
        ]
        order = cal.sequence(concepts)
        self.assertEqual(len(order), len(concepts))
        self.assertEqual({c["title"] for c in order}, {c["title"] for c in concepts})

    def test_resolves_violations_when_a_conflict_free_ordering_exists(self):
        # Greedy front-loading by composite score packs all three A-format
        # concepts first (a same-format-3-days-running violation); a
        # conflict-free ordering exists (interleave the lone B), so the
        # hill-climb pass must find it.
        concepts = [
            {"title": "c1", "format": "A", "composite": 10, "audio_pick": ""},
            {"title": "c2", "format": "A", "composite": 9, "audio_pick": ""},
            {"title": "c3", "format": "A", "composite": 8, "audio_pick": ""},
            {"title": "c4", "format": "B", "composite": 7, "audio_pick": ""},
        ]
        order = cal.sequence(concepts)
        self.assertEqual(cal.total_violations(order), 0)

    def test_terminates_and_keeps_all_items_when_no_conflict_free_ordering_exists(self):
        # Every concept shares the same format and the same named audio, so a
        # 0-violation ordering is impossible; this only proves the hill-climb
        # guard terminates (it doesn't infinite-loop) and never drops an item.
        concepts = [
            {"title": f"c{i}", "format": "A", "composite": 10 - i, "audio_pick": "OnlySong"}
            for i in range(6)
        ]
        order = cal.sequence(concepts)
        self.assertEqual(len(order), 6)
        self.assertEqual({c["title"] for c in order}, {c["title"] for c in concepts})


if __name__ == "__main__":
    unittest.main()
