#!/usr/bin/env python3
"""Build the flat master.csv across every collection in manifest.json.

Consolidates what were three divergent per-run copies of this script into one
generic build. Kept the most correct behavior found across them:
  - dedup a shortcode saved to multiple collections into ONE row, with a
    `collections` column listing every folder it appears in (a bug in the
    oldest variant let the same shortcode appear as a duplicate row instead);
  - hashtag/mention extraction from the caption;
  - a derived `shareability` score (shares / likes band) where shares exist;
  - pass through optional judge columns (angle_score/verdict/critique) if an
    enrichment pass wrote them.

Non-video / login-gated items are never dropped: they get a row with a
`status` instead (see manual_overrides.json below).

Sources (all under --data-dir):
  manifest.json                 [{"slug","name"}, ...]
  feed-<slug>.json              {"reels":[{"code","mt","audio"}, ...]}  (mt: 1=photo, 2=reel, 8=carousel)
  metadata/<slug>/<code>.info.json   yt-dlp: exact counts/caption/date/creator/duration
  transcripts/<slug>/<code>.txt      raw whisper transcript (fallback if enrichment has none)
  enrichment.json               {code: {title, onscreen_text, about, why_it_works,
                                  recreation_angle, format_template, theme, tone, hook_type,
                                  audio_type, language, why_saved, lyrics, transcript,
                                  angle_score, angle_verdict, angle_critique}}  (all optional)
  manual_overrides.json         {code: {creator, likes, comments, date, caption, duration}}
                                  for items yt-dlp couldn't fetch (login-gated, deleted, photo)
  dl-status-<slug>.json         {code: "ok"|"gated"|"photo"|"error"|"pending"}

Usage: python3 build_master.py [--data-dir DATA_DIR] [--out master.csv]
"""
import argparse
import csv
import datetime
import glob
import json
import os
import re
from collections import Counter

HASHTAG = re.compile(r"#[\wऀ-ॿ]+")
MENTION = re.compile(r"@[\w.]+")
MT_NAME = {1: "photo", 2: "reel", 8: "carousel"}

COLS = [
    "account", "collection", "collections", "media_type", "status", "reel_url", "shortcode",
    "creator_handle", "title", "caption", "hashtags", "mentions",
    "onscreen_text", "audio_name", "lyrics", "transcript", "audio_details",
    "views", "likes", "comments", "shares", "likes_int", "comments_int",
    "post_date", "duration_s",
    "thumbnail", "frame_1", "frame_2", "frame_3", "page_screenshot",
    "about", "why_it_works", "recreation_angle",
    "angle_score", "angle_verdict", "angle_critique",
    "format_template", "theme", "tone", "hook_type", "audio_type", "language",
    "why_saved", "shareability",
    "your_note", "tags", "captured_at",
]


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return d if d is not None else {}


def as_int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return ""


def shareability(likes, shares):
    try:
        l, s = int(likes), int(shares)
        if not l:
            return ""
        r = s / l
        return "viral" if r > .1 else "high" if r > .03 else "mid" if r > .008 else "low"
    except (ValueError, TypeError):
        return ""


def read_txt(root, slug, sc, limit=1500):
    p = f"{root}/transcripts/{slug}/{sc}.txt"
    if os.path.exists(p):
        return " ".join(open(p, encoding="utf-8").read().split())[:limit]
    return ""


def rel(root, sub, slug, sc, ext, suf=""):
    p = f"{sub}/{slug}/{sc}{suf}.{ext}"
    return p if os.path.exists(f"{root}/{p}") else ""


def first_candidate(root, slug, sc):
    hits = sorted(glob.glob(f"{root}/candidates/{slug}/{sc}/c*.jpg"))
    return hits[0].split(f"{root}/")[-1] if hits else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--account", default="", help="value written to the account column (optional)")
    ap.add_argument("--out", default="master.csv")
    ap.add_argument("--captured-at", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    root = args.data_dir

    manifest = load(f"{root}/manifest.json", {"collections": []})
    order = [(c["slug"], c["name"]) for c in manifest.get("collections", [])]
    if not order:
        raise SystemExit(f"No collections found in {root}/manifest.json — nothing to build.")

    enrichment = load(f"{root}/enrichment.json")
    overrides = load(f"{root}/manual_overrides.json")

    by_sc = {}       # shortcode -> row dict (with a private "_colls" list)
    sc_order = []
    for slug, cname in order:
        feed = load(f"{root}/feed-{slug}.json")
        status_map = load(f"{root}/dl-status-{slug}.json")
        for r in feed.get("reels", []):
            sc = r["code"]
            if sc in by_sc:  # cross-collection duplicate: just record the extra collection
                if cname not in by_sc[sc]["_colls"]:
                    by_sc[sc]["_colls"].append(cname)
                continue
            sc_order.append(sc)

            info = load(f"{root}/metadata/{slug}/{sc}.info.json")
            man = overrides.get(sc, {})
            e = enrichment.get(sc, {})
            st = status_map.get(sc) or ("ok" if info else "pending")

            ts = info.get("timestamp") or man.get("ts")
            date = (datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")
                    if ts else man.get("date", ""))
            media_type = MT_NAME.get(r.get("mt"), "reel")
            likes = info.get("like_count") if info.get("like_count") is not None else man.get("likes", "")
            comments = info.get("comment_count") if info.get("comment_count") is not None else man.get("comments", "")
            shares = e.get("shares", "") or man.get("shares", "")
            caption = (info.get("description") or man.get("caption", "") or "").strip()
            transcript = e.get("transcript") or read_txt(root, slug, sc)

            row = {
                "_colls": [cname],
                "media_type": media_type, "status": st,
                "reel_url": f"https://www.instagram.com/{'reel' if media_type == 'reel' else 'p'}/{sc}/",
                "shortcode": sc,
                "creator_handle": info.get("channel") or info.get("uploader_id") or man.get("creator", ""),
                "title": e.get("title", ""),
                "caption": caption,
                "hashtags": " ".join(HASHTAG.findall(caption)),
                "mentions": " ".join(dict.fromkeys(MENTION.findall(caption))),
                "onscreen_text": e.get("onscreen_text", ""),
                "audio_name": r.get("audio") or man.get("audio_name", ""),
                "lyrics": e.get("lyrics", ""),
                "transcript": transcript,
                "audio_details": "",
                "views": "", "likes": likes, "comments": comments, "shares": shares,
                "likes_int": as_int(likes), "comments_int": as_int(comments),
                "post_date": date, "duration_s": info.get("duration") or man.get("duration", ""),
                "thumbnail": rel(root, "thumbnails", slug, sc, "jpg") or first_candidate(root, slug, sc),
                "frame_1": rel(root, "frames_multi", slug, sc, "jpg", "_1") or first_candidate(root, slug, sc),
                "frame_2": rel(root, "frames_multi", slug, sc, "jpg", "_2"),
                "frame_3": rel(root, "frames_multi", slug, sc, "jpg", "_3"),
                "page_screenshot": rel(root, "screenshots", slug, sc, "png", "_page"),
                "about": e.get("about", ""), "why_it_works": e.get("why_it_works", ""),
                "recreation_angle": e.get("recreation_angle", ""),
                "angle_score": e.get("angle_score", ""), "angle_verdict": e.get("angle_verdict", ""),
                "angle_critique": e.get("angle_critique", ""),
                "format_template": e.get("format_template", ""), "theme": e.get("theme", ""),
                "tone": e.get("tone", ""), "hook_type": e.get("hook_type", ""),
                "audio_type": e.get("audio_type", ""), "language": e.get("language", ""),
                "why_saved": e.get("why_saved", ""), "shareability": shareability(likes, shares),
                "your_note": "", "tags": "", "captured_at": args.captured_at,
            }
            by_sc[sc] = row

    rows = []
    for sc in sc_order:
        row = by_sc[sc]
        colls = row.pop("_colls")
        row["account"] = args.account
        row["collection"] = colls[0]
        row["collections"] = "|".join(colls)
        rows.append(row)

    out_path = f"{root}/{args.out}"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} unique rows -> {out_path}")
    print("by status:", dict(Counter(r["status"] for r in rows)))
    print("by media :", dict(Counter(r["media_type"] for r in rows)))
    dups = sum(1 for r in rows if "|" in r["collections"])
    print(f"cross-collection duplicates merged: {dups}")


if __name__ == "__main__":
    main()
