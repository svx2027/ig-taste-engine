#!/usr/bin/env python3
"""Integrity-check a feed-<slug>.json against a browser-side djb2 signature.

Guarantees the shortcodes landed on disk exactly as the API returned them
(catches any transcription error in the browser -> context -> disk hop).

Usage: python3 verify_feed.py <feed.json> <expected_n> <expected_sig>
feed.json schema: {"slug":..., "reels":[{"code","mt","audio"}, ...]}
Prints OK / MISMATCH and exits non-zero on failure.
"""
import sys
import json


def djb2(s: str) -> int:
    h = 5381
    for ch in s:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return h


def main():
    feed, exp_n, exp_sig = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    d = json.load(open(feed))
    codes = [r["code"] for r in d["reels"]]
    n = len(codes)
    uniq = len(set(codes))
    bad = [c for c in codes if not (isinstance(c, str) and 5 <= len(c) <= 20)]
    sig = djb2(",".join(sorted(codes)))

    ok = (n == exp_n) and (sig == exp_sig) and (uniq == n) and not bad
    print(
        f"{'OK' if ok else 'MISMATCH'} slug={d.get('slug')} n={n} exp_n={exp_n} "
        f"uniq={uniq} sig={sig} exp_sig={exp_sig} bad_codes={bad[:3]}"
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
