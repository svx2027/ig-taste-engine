#!/usr/bin/env python3
"""Apply vision-workflow output: write onscreen_verbatim.json and copy the picked
frames into frames_multi/<slug>/<shortcode>_1..3.jpg.

Input: the JSON produced by vision_workflow.js (or any workflow with the same
shape) -- {"items": [{"shortcode", "onscreen_text", "keep_frames": [relative
paths, as found in candidates_index.json]}, ...]}, optionally wrapped in
{"result": {...}}.

Usage:
    python3 apply_picks.py <workflow_output.json> [--data-dir DATA_DIR]
"""
import argparse
import json
import os
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow_output")
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    base = args.data_dir
    obj = json.load(open(args.workflow_output, encoding="utf-8"))
    items = obj.get("result", {}).get("items", obj.get("items", []))
    idx = json.load(open(f"{base}/candidates_index.json"))

    onscreen, copied, framed = {}, 0, 0
    for it in items:
        sc = it.get("shortcode")
        if not sc:
            continue
        onscreen[sc] = (it.get("onscreen_text") or "").strip()
        slug = idx.get(sc, {}).get("slug")
        keep = [k for k in (it.get("keep_frames") or []) if k][:3]
        if slug and keep:
            outdir = f"{base}/frames_multi/{slug}"
            os.makedirs(outdir, exist_ok=True)
            n = 0
            for i, rel in enumerate(keep, 1):
                src = os.path.join(base, rel)
                if os.path.exists(src):
                    shutil.copyfile(src, f"{outdir}/{sc}_{i}.jpg")
                    n += 1
                    copied += 1
            if n:
                framed += 1

    json.dump(onscreen, open(f"{base}/onscreen_verbatim.json", "w"), ensure_ascii=False, indent=1)
    print(f"onscreen_verbatim: {len(onscreen)} | clips_with_frames: {framed} | frames_copied: {copied}")


if __name__ == "__main__":
    main()
