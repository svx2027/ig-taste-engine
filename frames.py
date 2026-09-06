#!/usr/bin/env python3
"""Extract punchline-aware candidate frames for every downloaded reel.

Candidates = time-samples (10/30/50/72/90% of duration, or 40/80% for clips
under 3s) UNION up to 3 scene-cut frames (ffmpeg `select=gt(scene,0.4)`), each
640px wide. Resumable: skips any shortcode that already has candidates indexed.
Writes candidates_index.json {shortcode: {slug, candidates: [relative paths]}}.
Run repeatedly as downloads land (see run_offline.sh).

Consolidates what were two divergent implementations in earlier runs of this
pipeline (a hardcoded-slug-list version and a feed-glob version) into one:
this is the feed-glob version, since it scales to any number of collections
without editing the script, and it is resumable across accounts/collections.

Usage: python3 frames.py [--data-dir DATA_DIR]
"""
import argparse
import glob
import json
import os
import subprocess


def dur(path):
    try:
        return float(
            subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                capture_output=True, text=True,
            ).stdout.strip()
        )
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()
    root = args.data_dir

    feeds = sorted(glob.glob(f"{root}/feed-*.json"))
    ipath = f"{root}/candidates_index.json"
    index = json.load(open(ipath)) if os.path.exists(ipath) else {}

    new = 0
    for fp in feeds:
        feed = json.load(open(fp))
        slug = feed["slug"]
        for r in feed["reels"]:
            sc = r["code"]
            v = f"{root}/videos/{slug}/{sc}.mp4"
            if not os.path.exists(v):
                continue
            if sc in index and index[sc].get("candidates"):
                continue  # already framed
            cdir = f"{root}/candidates/{slug}/{sc}"
            os.makedirs(cdir, exist_ok=True)
            D = dur(v)
            fracs = [0.4, 0.8] if D and D < 3 else [0.10, 0.30, 0.50, 0.72, 0.90]
            cands = []
            for j, fr in enumerate(fracs):
                t = round(fr * D, 2) if D else j
                out = f"{cdir}/c{j:02d}.jpg"
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-ss", str(t), "-i", v, "-frames:v", "1",
                     "-vf", "scale=640:-2", "-q:v", "2", out, "-y"],
                    capture_output=True,
                )
                if os.path.exists(out):
                    cands.append(f"candidates/{slug}/{sc}/c{j:02d}.jpg")
            if D and D >= 4:
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-i", v, "-vf",
                     "select=gt(scene\\,0.4),scale=640:-2", "-vsync", "vfr", "-frames:v", "3",
                     "-q:v", "2", f"{cdir}/s%02d.jpg", "-y"],
                    capture_output=True,
                )
                for sf in sorted(glob.glob(f"{cdir}/s*.jpg")):
                    cands.append(f"candidates/{slug}/{sc}/" + os.path.basename(sf))
            index[sc] = {"slug": slug, "candidates": cands}
            new += 1

    json.dump(index, open(ipath, "w"), indent=1)
    tot = sum(len(v["candidates"]) for v in index.values())
    print(f"FRAMES_DONE clips_indexed={len(index)} new_this_run={new} total_candidates={tot}", flush=True)


if __name__ == "__main__":
    main()
