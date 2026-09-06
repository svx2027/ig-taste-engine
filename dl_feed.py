#!/usr/bin/env python3
"""Download every reel in a feed-<slug>.json via yt-dlp (anonymous, account-safe).

Resumable: skips reels whose .mp4 already exists. Classifies each:
  ok    -> video+thumb+info.json saved
  gated -> yt-dlp 'empty media' (login-gated) -> needs a manual_overrides.json entry
  photo -> 'no video in this post' (photo/carousel)
  error -> other failure
Writes dl-status-<slug>.json.

Never given your browser's login cookies: gated content is left for you to
capture by hand (metadata + a page screenshot), never fetched with your session.

Usage: python3 dl_feed.py <feed.json> [--data-dir DATA_DIR] [--yt-dlp PATH]
Env: DL_PACE=<seconds> to sleep between real download attempts (default 0).
"""
import argparse
import json
import os
import subprocess
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed_json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--yt-dlp", default="yt-dlp", help="path to the yt-dlp binary")
    args = ap.parse_args()

    root = args.data_dir
    pace = float(os.environ.get("DL_PACE", "0"))

    feed = json.load(open(args.feed_json))
    slug = feed["slug"]
    reels = feed["reels"]
    vid_dir = f"{root}/videos/{slug}"
    thb_dir = f"{root}/thumbnails/{slug}"
    meta_dir = f"{root}/metadata/{slug}"
    for d in (vid_dir, thb_dir, meta_dir):
        os.makedirs(d, exist_ok=True)

    spath = f"{root}/dl-status-{slug}.json"
    status = json.load(open(spath)) if os.path.exists(spath) else {}

    total = len(reels)
    done = 0
    for r in reels:
        sc = r["code"]
        mp4 = f"{vid_dir}/{sc}.mp4"
        done += 1
        if os.path.exists(mp4):
            status[sc] = status.get(sc, "ok")
            continue
        if pace:
            time.sleep(pace)
        p = subprocess.run(
            [
                args.yt_dlp,
                f"https://www.instagram.com/reel/{sc}/",
                "-o", f"{vid_dir}/{sc}.%(ext)s",
                "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
                "--no-warnings", "-q",
            ],
            capture_output=True, text=True,
        )
        err = (p.stderr or "") + (p.stdout or "")
        if os.path.exists(mp4):
            for ext, dst in ((".info.json", meta_dir), (".jpg", thb_dir)):
                srcp = f"{vid_dir}/{sc}{ext}"
                if os.path.exists(srcp):
                    os.replace(srcp, f"{dst}/{sc}{ext}")
            status[sc] = "ok"
        elif "empty media response" in err or "login" in err.lower() or "cookies" in err.lower():
            status[sc] = "gated"
        elif "no video" in err.lower():
            status[sc] = "photo"
        else:
            status[sc] = "error"
        if done % 5 == 0 or done == total:
            json.dump(status, open(spath, "w"), indent=0)
            print(f"[{slug}] {done}/{total} last={sc}:{status[sc]}", flush=True)

    json.dump(status, open(spath, "w"), indent=1)
    from collections import Counter
    c = Counter(status.values())
    print(f"DONE {slug}: {dict(c)}", flush=True)


if __name__ == "__main__":
    main()
