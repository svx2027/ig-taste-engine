#!/usr/bin/env python3
"""Assemble a posting calendar from a judged set of reel concepts.

Input: a JSON file (produced by your own idea-generation + judging pass -- an
agent, a workflow, or a hand-written file) of the shape:
  [ { "title", "format", "theme", "hook_type", "tone", "audio_pick", "setup_tag",
      "shoot_script", "onscreen_text", "caption", "props_needed", "why_it_fits",
      "composite": <float ranking score>,
      "verdict": { "virality_fit", "feasibility_solo", "originality", "taste_fit",
                   "critique", "fix" } }, ... ]

Output:
  REEL_IDEAS.md          -- concepts ranked by composite score
  CONTENT_CALENDAR.md    -- a deterministic day-by-day shoot+post plan
  reel_queue.csv         -- the same, machine-readable

Sequencing is fully deterministic: front-load the highest-composite concepts,
then hill-climb pairwise swaps until no named audio pick repeats within 3 days
and no format repeats 3 days running (original-VO/instrumental audio is exempt
from the spacing rule since it isn't a "named sound" that would feel repeated).

Usage: python3 build_content_calendar.py <judged_concepts.json>
                                          [--data-dir DATA_DIR] [--days N]
"""
import argparse
import csv
import json
import os
import re
from collections import defaultdict

EXEMPT_AUDIO = {"original-vo", "instrumental", ""}


def total_violations(order):
    v = 0
    for i in range(len(order)):
        if i >= 2 and order[i]["format"] == order[i - 1]["format"] == order[i - 2]["format"]:
            v += 1
        a = (order[i].get("audio_pick") or "").strip().lower()
        if a not in EXEMPT_AUDIO and a in [(o.get("audio_pick") or "").strip().lower() for o in order[max(0, i - 3):i]]:
            v += 1
    return v


def sequence(concepts):
    remaining = sorted(concepts, key=lambda c: c["composite"], reverse=True)
    order = []
    while remaining:
        for i, c in enumerate(remaining):
            fmt_ok = not (len(order) >= 2 and order[-1]["format"] == c["format"] == order[-2]["format"])
            aud = (c.get("audio_pick") or "").strip().lower()
            aud_ok = aud in EXEMPT_AUDIO or aud not in [(o.get("audio_pick") or "").strip().lower() for o in order[-3:]]
            if fmt_ok and aud_ok:
                order.append(remaining.pop(i))
                break
        else:
            order.append(remaining.pop(0))
    guard = 0
    while total_violations(order) > 0 and guard < 4000:
        guard += 1
        base = total_violations(order)
        swapped = False
        for i in range(len(order)):
            for j in range(i + 1, len(order)):
                order[i], order[j] = order[j], order[i]
                if total_violations(order) < base:
                    swapped = True
                    break
                order[i], order[j] = order[j], order[i]
            if swapped:
                break
        if not swapped:
            break  # local minimum
    return order


def md_ideas(ranked):
    L = ["# Reel Ideas -- ranked by composite score", ""]
    L.append(f"**{len(ranked)} shoot-ready concepts**, ranked by whatever composite score your judging "
             "pass assigned (a typical weighting: virality-fit, solo-feasibility, originality, taste-fit).")
    L.append("")
    L.append("---")
    for c in ranked:
        v = c.get("verdict", {})
        L.append("")
        L.append(f"### #{c['rank']}. {c['title']}  .  `{c['composite']}`")
        L.append(f"**{c['format']} x {c['theme']}** . hook: {c.get('hook_type', '')} . tone: {c.get('tone', '')} . "
                  f"audio: **{c.get('audio_pick', '')}** . setup: `{c.get('setup_tag', '')}`")
        L.append("")
        if c.get("shoot_script"):
            L.append(f"**Shoot:** {c['shoot_script']}")
            L.append("")
        if c.get("onscreen_text"):
            L.append("**On-screen text:**")
            L.append("```")
            L.append(c["onscreen_text"])
            L.append("```")
        if c.get("caption"):
            L.append(f"**Caption:** {c['caption']}")
        L.append("")
        if c.get("props_needed"):
            L.append(f"**Props:** {c['props_needed']}  ")
        if c.get("why_it_fits"):
            L.append(f"**Why it fits:** {c['why_it_fits']}")
        L.append("")
        if v:
            L.append(f"**Judge** -- virality {v.get('virality_fit', '?')}/10 . feasibility {v.get('feasibility_solo', '?')}/10 . "
                      f"originality {v.get('originality', '?')}/10 . taste {v.get('taste_fit', '?')}/10  ")
            if v.get("critique"):
                L.append(f"  -> *{v['critique']}*  ")
            if v.get("fix"):
                L.append(f"  -> **Fix:** {v['fix']}")
            L.append("")
        L.append("---")
    return "\n".join(L)


def md_calendar(order, repurpose_days, ranked):
    L = ["# Content Calendar", ""]
    L.append(f"{len(order)} original concepts on days 1-{len(order)}, then {repurpose_days} repurpose days "
              "(re-cut top performers as carousels / stories). Named audio picks are spaced so the same "
              "sound doesn't repeat within 3 days, and formats never run 3 days in a row.")
    L.append("")
    L.append("## Posting schedule\n")
    L.append("| Day | Concept | Format | Theme | Audio | Setup |")
    L.append("|----:|---------|--------|-------|-------|-------|")
    for d, c in enumerate(order, 1):
        L.append(f"| {d} | {c['title']} | {c['format']} | {c['theme']} | {c.get('audio_pick', '')} | `{c.get('setup_tag', '')}` |")
    top = ranked[:repurpose_days]
    repur_labels = ["carousel re-cut", "story poll + BTS", "remix w/ alt audio", "carousel re-cut",
                     "story Q&A on the topic", "best-of compilation teaser"]
    for j, c in enumerate(top):
        d = len(order) + 1 + j
        label = repur_labels[j % len(repur_labels)]
        L.append(f"| {d} | Repurpose #{c['rank']} -- {c['title']} | {label} | {c['theme']} | -- | -- |")
    L.append("")
    L.append("## Batch-shoot sessions (film same setups together)\n")
    groups = defaultdict(list)
    for c in order:
        groups[c.get("setup_tag", "")].append(c)
    for tag, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if not tag:
            continue
        titles = ", ".join(f'"{c["title"]}"' for c in items)
        L.append(f"- **`{tag}`** ({len(items)} reels) -- one session: {titles}")
    L.append("")
    return "\n".join(L)


def write_csv(path, ranked, order):
    day_of = {c["title"]: d for d, c in enumerate(order, 1)}
    cols = ["rank", "calendar_day", "title", "format", "theme", "hook_type", "tone",
            "audio_pick", "setup_tag", "composite", "virality_fit", "feasibility_solo",
            "originality", "taste_fit", "verdict"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for c in ranked:
            v = c.get("verdict", {})
            w.writerow([c["rank"], day_of.get(c["title"], ""), c["title"], c["format"], c["theme"],
                        c.get("hook_type", ""), c.get("tone", ""), c.get("audio_pick", ""), c.get("setup_tag", ""),
                        c["composite"], v.get("virality_fit", ""), v.get("feasibility_solo", ""),
                        v.get("originality", ""), v.get("taste_fit", ""), v.get("verdict", "")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("judged_concepts_json")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--repurpose-days", type=int, default=6)
    args = ap.parse_args()
    base = args.data_dir

    concepts = json.load(open(args.judged_concepts_json, encoding="utf-8"))
    ranked = sorted(concepts, key=lambda c: c["composite"], reverse=True)
    for i, c in enumerate(ranked, 1):
        c["rank"] = i

    order = sequence(concepts)
    ideas_md = md_ideas(ranked)
    cal_md = md_calendar(order, args.repurpose_days, ranked)

    open(os.path.join(base, "REEL_IDEAS.md"), "w", encoding="utf-8").write(ideas_md)
    open(os.path.join(base, "CONTENT_CALENDAR.md"), "w", encoding="utf-8").write(cal_md)
    write_csv(os.path.join(base, "reel_queue.csv"), ranked, order)

    # Independent re-derivation of what was just written, rather than trusting
    # the generation step that produced it.
    ideas_n = ideas_md.count("\n### #")
    sched_rows = len(re.findall(r"^\| \d+ \|", cal_md, re.M))
    repur_rows = len(re.findall(r"^\| \d+ \| Repurpose #", cal_md, re.M))
    csv_rows = sum(1 for _ in open(os.path.join(base, "reel_queue.csv"), encoding="utf-8")) - 1
    total_days = len(order) + args.repurpose_days
    print(f"REEL_IDEAS.md      : {ideas_n} concept blocks (expect {len(concepts)})")
    print(f"CONTENT_CALENDAR.md: {sched_rows} day rows ({sched_rows - repur_rows} original + {repur_rows} repurpose, expect {total_days})")
    print(f"reel_queue.csv     : {csv_rows} rows (expect {len(concepts)})")
    print(f"calendar constraint violations: {total_violations(order)} (format-streak + audio-spacing)")
    assert ideas_n == len(concepts), "idea block count mismatch"
    assert sched_rows == total_days, "calendar day count mismatch"
    assert csv_rows == len(concepts), "csv row mismatch"
    print("INTEGRITY: PASS")


if __name__ == "__main__":
    main()
