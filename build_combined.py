#!/usr/bin/env python3
"""Merge two master*.csv files (e.g. two separate capture runs, or two accounts)
into one master_combined.csv. Dedups by shortcode, takes the superset of
columns, and derives:
  - `folder_intent`: a lightweight classification of each collection name as
    "recreate" (name contains recreate/remake/redo/easy), "negative" (name
    contains dont/shouldnt — a "why this doesn't work" reference folder), or
    "reference" (everything else). This is a generic keyword rule; if your own
    collection names need more nuance, extend RECREATE_KW / NEGATIVE_KW below
    rather than hardcoding folder names.
  - `cross_save_weight`: how many collections a shortcode was saved to.

Usage: python3 build_combined.py <master_a.csv> <master_b.csv>
                                  [--data-dir DATA_DIR] [--out master_combined.csv]
"""
import argparse
import csv
import os
import re

RECREATE_KW = re.compile(r'(?i)\b(recreate|remake|redo|easy)\b')
NEGATIVE_KW = re.compile(r'(?i)\b(dont|shouldnt|don\'t|shouldn\'t)\b')

COLS = [
    "account", "collection", "collections", "media_type", "status",
    "reel_url", "shortcode", "creator_handle", "title", "caption",
    "hashtags", "mentions",
    "onscreen_text", "audio_name", "lyrics", "transcript", "audio_details",
    "views", "likes", "comments", "shares",
    "likes_int", "comments_int",
    "post_date", "duration_s",
    "thumbnail", "frame_1", "frame_2", "frame_3", "page_screenshot",
    "about", "why_it_works", "recreation_angle",
    "angle_score", "angle_verdict", "angle_critique",
    "format_template", "theme", "tone", "hook_type", "audio_type",
    "language", "why_saved", "shareability",
    "your_note", "tags", "captured_at",
    "folder_intent", "cross_save_weight",
]


def classify_collection(name):
    name = name.strip()
    if not name:
        return ""
    if RECREATE_KW.search(name):
        return "recreate"
    if NEGATIVE_KW.search(name):
        return "negative"
    return "reference"


def extract_hashtags(caption):
    return "|".join(re.findall(r'#[\wऀ-ॿ]+', caption or ""))


def extract_mentions(caption):
    return "|".join(re.findall(r'@[\w.]+', caption or ""))


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master_a")
    ap.add_argument("master_b")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="master_combined.csv")
    args = ap.parse_args()

    a = load_csv(args.master_a)
    b = load_csv(args.master_b)
    print(f"file A: {len(a)} rows")
    print(f"file B: {len(b)} rows")

    a_by_sc = {r["shortcode"]: r for r in a}
    b_by_sc = {r["shortcode"]: r for r in b}
    all_sc = set(a_by_sc) | set(b_by_sc)
    overlap = set(a_by_sc) & set(b_by_sc)
    print(f"overlap: {len(overlap)}")
    print(f"union:   {len(all_sc)}")

    combined = []
    for sc in sorted(all_sc):
        in_a, in_b = sc in a_by_sc, sc in b_by_sc
        if in_a and in_b:
            base = dict(b_by_sc[sc])  # prefer B's richer fields where both have data
            ar = a_by_sc[sc]
            cols_set = set()
            for r in (base, ar):
                col = (r.get("collection") or "").strip()
                if col:
                    cols_set.add(col)
                for c in (r.get("collections") or "").split("|"):
                    if c.strip():
                        cols_set.add(c.strip())
            base["collections"] = "|".join(sorted(cols_set))
            for k in ar:
                if not (base.get(k) or "").strip() and (ar.get(k) or "").strip():
                    base[k] = ar[k]
        elif in_a:
            base = dict(a_by_sc[sc])
            if not (base.get("hashtags") or "").strip():
                base["hashtags"] = extract_hashtags(base.get("caption", ""))
            if not (base.get("mentions") or "").strip():
                base["mentions"] = extract_mentions(base.get("caption", ""))
        else:
            base = dict(b_by_sc[sc])

        if not (base.get("collections") or "").strip():
            col = (base.get("collection") or "").strip()
            if col:
                base["collections"] = col
        cols_list = sorted({c.strip() for c in (base.get("collections") or "").split("|") if c.strip()})
        base["collections"] = "|".join(cols_list)

        intents = {classify_collection(c) for c in cols_list}
        intents.discard("")
        base["folder_intent"] = "|".join(sorted(intents))
        base["cross_save_weight"] = str(len(cols_list)) if cols_list else "1"

        combined.append({k: base.get(k, "") for k in COLS})

    combined.sort(key=lambda r: (r["collection"], r["shortcode"]))

    out_path = os.path.join(args.data_dir, args.out)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(combined)

    print(f"\nWrote {len(combined)} rows -> {out_path}")

    # Independent re-derivation, not a trust-the-script assertion: recompute the
    # union/overlap counts from the output file itself.
    check = load_csv(out_path)
    shortcodes = [r["shortcode"] for r in check]
    assert len(shortcodes) == len(set(shortcodes)), "duplicate shortcodes in output"
    assert len(check) == len(all_sc), f"row count {len(check)} != expected union {len(all_sc)}"
    from collections import Counter
    print("folder_intent distribution:", dict(Counter(
        i for r in check for i in r["folder_intent"].split("|") if i.strip()
    )))
    print("cross_save_weight distribution:", dict(Counter(
        int(r["cross_save_weight"]) for r in check
    )))
    print("INTEGRITY: PASS")


if __name__ == "__main__":
    main()
