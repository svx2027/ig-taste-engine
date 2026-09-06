#!/usr/bin/env python3
"""Build vision-worklist.json: one entry per video reel that has candidate frames,
with the context an enrichment agent could use (audio name, caption head,
transcript head, creator, candidate frame paths).

This is an OPTIONAL, richer alternative manifest for anyone wiring up their own
enrichment pass. The shipped vision_workflow.js does not read this file -- it
works directly off candidates_index.json and only produces on-screen-text +
frame picks, not taste labels. Use this script's output if you want your own
vision/enrichment step to have audio/caption/transcript context too.

Usage: python3 make_vision_worklist.py [--data-dir DATA_DIR] [--collection SLUG]

Without --collection, every collection in manifest.json is processed. With it,
only that one slug is (matches a single-collection capture run); candidate
frames are looked up under that slug first, falling back to any other slug in
case the same shortcode was already framed via a cross-collection duplicate.
"""
import argparse
import glob
import json
import os


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return d if d is not None else {}


def candidates_for(root, slug, sc):
    cands = sorted(glob.glob(f"{root}/candidates/{slug}/{sc}/c*.jpg")) + \
        sorted(glob.glob(f"{root}/candidates/{slug}/{sc}/s*.jpg"))
    if not cands:
        cands = sorted(glob.glob(f"{root}/candidates/*/{sc}/c*.jpg")) + \
            sorted(glob.glob(f"{root}/candidates/*/{sc}/s*.jpg"))
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--collection", help="only build the worklist for this slug")
    ap.add_argument("--out", default=None, help="output filename (default: vision-worklist.json, "
                                                  "or vision-worklist-<collection>.json if --collection is set)")
    args = ap.parse_args()
    root = args.data_dir

    if args.collection:
        slugs = [args.collection]
    else:
        manifest = load(f"{root}/manifest.json", {"collections": []})
        slugs = [c["slug"] for c in manifest.get("collections", [])]

    work = []
    for slug in slugs:
        feed = load(f"{root}/feed-{slug}.json")
        for r in feed.get("reels", []):
            sc = r["code"]
            if r.get("mt") != 2:  # only videos (photos/carousels skip vision OCR of frames)
                continue
            cands = candidates_for(root, slug, sc)
            if not cands:
                continue
            info = load(f"{root}/metadata/{slug}/{sc}.info.json")
            tp = f"{root}/transcripts/{slug}/{sc}.txt"
            transcript = " ".join(open(tp, encoding="utf-8").read().split())[:600] if os.path.exists(tp) else ""
            work.append({
                "sc": sc, "slug": slug,
                "audio": r.get("audio") or "",
                "creator": info.get("channel", ""),
                "caption": (info.get("description") or "")[:400],
                "transcript": transcript,
                "candidates": [p.split(f"{root}/")[-1] for p in cands],
            })

    out = args.out or (f"vision-worklist-{args.collection}.json" if args.collection else "vision-worklist.json")
    json.dump(work, open(f"{root}/{out}", "w"), ensure_ascii=False, indent=1)
    print(f"vision worklist: {len(work)} video reels with candidate frames -> {out}")


if __name__ == "__main__":
    main()
