#!/usr/bin/env python3
"""Independent integrity re-derivation for master.csv -- re-counts everything
from the raw capture files rather than trusting build_master.py's own output.

Checks: unique rows == enumerated unique shortcodes (from feed-*.json, the
ground truth); every shortcode has a status; downloaded mp4s match 'ok' video
rows; enrichment/on-screen-text/frame coverage.

Usage: python3 verify_master.py [--data-dir DATA_DIR] [--master-csv master.csv]
"""
import argparse
import collections
import csv
import glob
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--master-csv", default="master.csv")
    ap.add_argument("--enrichment", default="enrichment.json")
    args = ap.parse_args()
    base = args.data_dir

    enum = {}
    for f in glob.glob(f"{base}/feed-*.json"):
        d = json.load(open(f))
        for r in d["reels"]:
            enum.setdefault(r["code"], r["mt"])
    enum_unique = set(enum)

    rows = list(csv.DictReader(open(os.path.join(base, args.master_csv), encoding="utf-8")))
    row_sc = [r["shortcode"] for r in rows]

    print("== INTEGRITY ==")
    print(f"enumerated unique shortcodes : {len(enum_unique)}")
    print(f"master rows                  : {len(rows)}")
    print(f"master unique shortcodes     : {len(set(row_sc))}")
    print(f"rows == unique?              : {len(row_sc) == len(set(row_sc))}")
    miss = enum_unique - set(row_sc)
    extra = set(row_sc) - enum_unique
    print(f"enumerated not in master     : {len(miss)} {sorted(miss)[:5]}")
    print(f"master not in enumerated     : {len(extra)} {sorted(extra)[:5]}")

    print("\nby status:", dict(collections.Counter(r["status"] for r in rows)))
    print("by media :", dict(collections.Counter(r["media_type"] for r in rows)))
    blank_status = [r["shortcode"] for r in rows if not r["status"] or r["status"] == "pending"]
    print(f"rows with blank/pending status: {len(blank_status)} {blank_status[:5]}")

    mp4 = {os.path.basename(p)[:-4] for p in glob.glob(f"{base}/videos/*/*.mp4")}
    ok_video = [r for r in rows if r["media_type"] == "reel" and r["status"] == "ok"]
    no_file = [r["shortcode"] for r in ok_video if r["shortcode"] not in mp4]
    print(f"\nmp4 files on disk           : {len(mp4)}")
    print(f"'ok' video rows             : {len(ok_video)}")
    print(f"ok-video rows missing mp4   : {len(no_file)} {no_file[:5]}")

    enr_path = os.path.join(base, args.enrichment)
    enr = json.load(open(enr_path)) if os.path.exists(enr_path) else {}
    enr_rows = [r for r in rows if r["shortcode"] in enr]
    print(f"\nrows with enrichment        : {len(enr_rows)}/{len(ok_video)} ok-videos")
    has_ocr = sum(1 for r in rows if r["onscreen_text"].strip())
    has_f1 = sum(1 for r in rows if r["frame_1"])
    print(f"rows with on-screen text    : {has_ocr}")
    print(f"rows with >=1 frame         : {has_f1}")
    print(f"rows with cover thumbnail   : {sum(1 for r in rows if r['thumbnail'])}")

    ok = (len(row_sc) == len(set(row_sc)) and not miss and not extra and not blank_status and not no_file)
    print("\nRESULT:", "PASS -- every enumerated reel is a unique row with a status & media" if ok else "CHECK ABOVE")


if __name__ == "__main__":
    main()
