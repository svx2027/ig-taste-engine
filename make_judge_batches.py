#!/usr/bin/env python3
"""Build judge batches for a second-pass quality check: each entry is a
recreation_angle plus minimal context, to be scored 1-5 on specificity and
feasibility by a separate judging pass. Text-only (cheap).

Usage: python3 make_judge_batches.py [--data-dir DATA_DIR] [--enrichment enrichment.json]
                                      [--batch-size 25]
"""
import argparse
import json
import math
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--enrichment", default="enrichment.json")
    ap.add_argument("--batch-size", type=int, default=25)
    args = ap.parse_args()
    root = args.data_dir

    enr = json.load(open(os.path.join(root, args.enrichment), encoding="utf-8"))
    items = []
    for sc, e in enr.items():
        ang = (e.get("recreation_angle") or "").strip()
        if not ang:
            continue
        items.append({
            "sc": sc, "title": e.get("title", ""),
            "about": (e.get("about", "") or "")[:240],
            "onscreen": (e.get("onscreen_text", "") or "")[:160],
            "format": e.get("format_template", ""), "theme": e.get("theme", ""),
            "recreation_angle": ang,
        })

    out_dir = os.path.join(root, "judge-batches")
    os.makedirs(out_dir, exist_ok=True)
    B = args.batch_size
    n = math.ceil(len(items) / B) if items else 0
    for i in range(n):
        json.dump(items[i * B:(i + 1) * B], open(f"{out_dir}/jb-{i:02d}.json", "w"), ensure_ascii=False)
    print(f"judge items: {len(items)} -> {n} batches in {out_dir}")


if __name__ == "__main__":
    main()
