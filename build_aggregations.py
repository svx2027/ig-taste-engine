#!/usr/bin/env python3
"""Build audio_library.csv (recurring sounds, 2+ uses) and creator_leaderboard.csv
(most-saved creators) from master.csv.

Usage: python3 build_aggregations.py [--data-dir DATA_DIR] [--master-csv master.csv]
"""
import argparse
import csv
import os
from collections import defaultdict


def as_int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return 0


def collections_of(row):
    return [c.strip() for c in (row.get("collections") or row.get("collection", "")).split("|") if c.strip()]


def build_audio_library(rows, out_path):
    groups = defaultdict(list)
    canonical = {}
    for r in rows:
        name = (r.get("audio_name") or "").strip()
        if not name:
            continue
        key = name.lower()
        groups[key].append(r)
        canonical.setdefault(key, name)

    audio_rows = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        at_counts = defaultdict(int)
        for r in group:
            at = (r.get("audio_type") or "").strip()
            if at:
                at_counts[at] += 1
        top_at = max(at_counts, key=at_counts.get) if at_counts else ""
        shortcodes = [r["shortcode"] for r in group]
        collections = sorted({c for r in group for c in collections_of(r)})
        likes_vals = [as_int(r.get("likes_int", "")) for r in group]
        avg_likes = round(sum(likes_vals) / len(likes_vals)) if likes_vals else 0
        top_reel = max(group, key=lambda r: as_int(r.get("likes_int", "")))
        audio_rows.append({
            "audio_name": canonical[key], "count": len(group), "audio_type": top_at,
            "shortcodes": "|".join(shortcodes), "collections": "|".join(collections),
            "avg_likes": avg_likes, "top_reel_url": top_reel.get("reel_url", ""),
        })
    audio_rows.sort(key=lambda r: r["count"], reverse=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["audio_name", "count", "audio_type", "shortcodes",
                                           "collections", "avg_likes", "top_reel_url"])
        w.writeheader()
        w.writerows(audio_rows)
    print(f"=== Audio library ===\nWrote {len(audio_rows)} recurring sounds -> {out_path}")
    if audio_rows:
        print("Top 10 recurring sounds:")
        for r in audio_rows[:10]:
            print(f"  {r['count']}x {r['audio_name']} ({r['audio_type']}) avg_likes={r['avg_likes']}")
    return audio_rows


def build_creator_leaderboard(rows, out_path):
    groups = defaultdict(list)
    for r in rows:
        handle = (r.get("creator_handle") or "").strip()
        if handle:
            groups[handle].append(r)

    creator_rows = []
    for handle, group in groups.items():
        collections = sorted({c for r in group for c in collections_of(r)})
        likes_vals = [as_int(r.get("likes_int", "")) for r in group]
        avg_likes = round(sum(likes_vals) / len(likes_vals)) if likes_vals else 0
        fmt_counts = defaultdict(int)
        for r in group:
            fmt = (r.get("format_template") or "").strip()
            if fmt:
                fmt_counts[fmt] += 1
        top_format = max(fmt_counts, key=fmt_counts.get) if fmt_counts else ""
        themes = sorted({(r.get("theme") or "").strip() for r in group if (r.get("theme") or "").strip()})
        top_reel = max(group, key=lambda r: as_int(r.get("likes_int", "")))
        creator_rows.append({
            "creator_handle": handle, "saves_count": len(group), "collections": "|".join(collections),
            "avg_likes": avg_likes, "top_format": top_format, "themes": "|".join(themes),
            "top_reel_url": top_reel.get("reel_url", ""),
        })
    creator_rows.sort(key=lambda r: r["saves_count"], reverse=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["creator_handle", "saves_count", "collections",
                                           "avg_likes", "top_format", "themes", "top_reel_url"])
        w.writeheader()
        w.writerows(creator_rows)
    no_handle = sum(1 for r in rows if not (r.get("creator_handle") or "").strip())
    print(f"\n=== Creator leaderboard ===\nWrote {len(creator_rows)} creators -> {out_path}")
    print(f"rows with no creator_handle: {no_handle}")
    if creator_rows:
        print("Top 15 creators:")
        for r in creator_rows[:15]:
            print(f"  {r['saves_count']}x @{r['creator_handle']} (avg {r['avg_likes']} likes, format={r['top_format']})")
    return creator_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--master-csv", default="master.csv")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(os.path.join(args.data_dir, args.master_csv), encoding="utf-8")))

    audio_rows = build_audio_library(rows, os.path.join(args.data_dir, "audio_library.csv"))
    creator_rows = build_creator_leaderboard(rows, os.path.join(args.data_dir, "creator_leaderboard.csv"))

    # Independent re-derivation: every row with a shared audio name should be
    # counted in exactly one audio_library group.
    reels_with_shared_audio = 0
    seen = defaultdict(int)
    for r in rows:
        name = (r.get("audio_name") or "").strip().lower()
        if name:
            seen[name] += 1
    for r in rows:
        name = (r.get("audio_name") or "").strip().lower()
        if name and seen[name] >= 2:
            reels_with_shared_audio += 1
    total_shared_sc = sum(a["count"] for a in audio_rows)
    assert total_shared_sc == reels_with_shared_audio, \
        f"Mismatch: {total_shared_sc} != {reels_with_shared_audio}"
    total_saves = sum(c["saves_count"] for c in creator_rows)
    no_handle = sum(1 for r in rows if not (r.get("creator_handle") or "").strip())
    assert total_saves + no_handle == len(rows), \
        f"saves_count sum mismatch: {total_saves} + {no_handle} != {len(rows)}"
    print("\nINTEGRITY: PASS")


if __name__ == "__main__":
    main()
