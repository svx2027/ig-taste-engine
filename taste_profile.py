#!/usr/bin/env python3
"""Distil a one-page Taste Profile (TASTE_PROFILE.md) from master.csv: top formats,
themes, tone, hooks, audio types, language mix, and highest-engagement saves.

Consolidates what were two versions of this script (a simple single-run one and
a richer one for a merged multi-run master) into one: the multi-run sections
(cross-save insights, recreate vs reference split, audio identity, creator
leaderboard, judged recreation angles) only appear when master.csv actually has
the columns they need (cross_save_weight, folder_intent, angle_score), and the
audio/creator sections read audio_library.csv / creator_leaderboard.csv if
build_aggregations.py has already been run.

Usage: python3 taste_profile.py [--data-dir DATA_DIR] [--master-csv master.csv]
"""
import argparse
import csv
import os
from collections import Counter


def as_int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return 0


def topn(rows, field, n=8):
    c = Counter((r.get(field) or "").strip() for r in rows if (r.get(field) or "").strip())
    return c.most_common(n)


def fmt(pairs, total):
    if not total:
        return "(no data)"
    return " . ".join(f"{k} ({v}, {round(100 * v / total)}%)" for k, v in pairs)


def section(rows, title, field, n=8):
    return f"- **{title}** -- {fmt(topn(rows, field, n), len(rows))}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--master-csv", default="master.csv")
    ap.add_argument("--out", default="TASTE_PROFILE.md")
    args = ap.parse_args()
    base = args.data_dir

    rows = list(csv.DictReader(open(os.path.join(base, args.master_csv), encoding="utf-8")))
    vid = [r for r in rows if r.get("media_type") == "reel"]
    N = len(vid)
    has = rows[0].keys() if rows else set()
    is_combined = "cross_save_weight" in has or "folder_intent" in has

    n_collections = len({c.strip() for r in rows for c in
                          (r.get("collections") or r.get("collection", "")).split("|") if c.strip()})

    lines = []
    lines.append("# Taste Profile\n")
    lines.append(f"Built from **{len(rows)} saved items** ({N} video reels) across "
                  f"{n_collections or '?'} collections. Engagement is a point-in-time snapshot; "
                  "Instagram does not expose reel view counts.\n")

    lines.append("## Signature\n")
    lines.append(section(vid, "Top formats", "format_template"))
    lines.append(section(vid, "Dominant themes", "theme"))
    lines.append(section(vid, "Tone signature", "tone", 7))
    lines.append(section(vid, "Preferred hooks", "hook_type"))
    lines.append(section(vid, "Audio types", "audio_type", 6))
    lines.append(section(vid, "Language mix", "language", 5))
    lines.append(section(vid, "Why saved (inferred)", "why_saved", 6))
    lines.append("")

    if is_combined:
        multi_save = [r for r in vid if as_int(r.get("cross_save_weight", "1")) > 1]
        lines.append("## Cross-save insights (saved to multiple collections)\n")
        lines.append(f"{len(multi_save)} reels appear in 2+ collections -- the strongest taste signal.\n")
        if multi_save:
            lines.append(section(multi_save, "Formats (multi-save)", "format_template", 5))
            lines.append(section(multi_save, "Themes (multi-save)", "theme", 5))
            lines.append(section(multi_save, "Hooks (multi-save)", "hook_type", 5))
            lines.append("")

        recreate = [r for r in vid if "recreate" in (r.get("folder_intent") or "")]
        reference = [r for r in vid if "reference" in (r.get("folder_intent") or "")
                     and "recreate" not in (r.get("folder_intent") or "")]
        if recreate or reference:
            lines.append("## Recreate vs reference split\n")
            lines.append(f"**Recreate-intent:** {len(recreate)} reels "
                          f"({round(100 * len(recreate) / N) if N else 0}%)\n")
            lines.append(section(recreate, "Formats (recreate)", "format_template", 5))
            lines.append(section(recreate, "Themes (recreate)", "theme", 5))
            lines.append("")
            lines.append(f"**Reference-intent:** {len(reference)} reels "
                          f"({round(100 * len(reference) / N) if N else 0}%)\n")
            lines.append(section(reference, "Formats (reference)", "format_template", 5))
            lines.append(section(reference, "Themes (reference)", "theme", 5))
            lines.append("")

    audio_path = os.path.join(base, "audio_library.csv")
    if os.path.exists(audio_path):
        audio_rows = list(csv.DictReader(open(audio_path, encoding="utf-8")))
        named = [a for a in audio_rows if a["audio_name"].strip().lower() != "original audio"]
        lines.append("## Audio identity\n")
        lines.append(f"**{len(audio_rows)} sounds** appear 2+ times across the corpus.\n")
        if named:
            lines.append("Top named recurring sounds:\n")
            for a in named[:10]:
                lines.append(f"- **{a['count']}x** {a['audio_name']} ({a['audio_type']}) -- avg {a['avg_likes']} likes")
        lines.append("")

    creator_path = os.path.join(base, "creator_leaderboard.csv")
    if os.path.exists(creator_path):
        creator_rows = list(csv.DictReader(open(creator_path, encoding="utf-8")))
        lines.append("## Creator reference set (top 10)\n")
        for c in creator_rows[:10]:
            lines.append(f"- **{c['saves_count']}x** @{c['creator_handle']} -- "
                          f"avg {c['avg_likes']} likes, top format: {c['top_format']}")
        lines.append("")

    if "angle_score" in has:
        score5 = sorted((r for r in vid if (r.get("angle_score") or "").strip() == "5"),
                         key=lambda r: as_int(r.get("likes_int", "")), reverse=True)
        weak = sorted((r for r in vid if (r.get("angle_score") or "").strip() in ("1", "2")),
                       key=lambda r: as_int(r.get("likes_int", "")), reverse=True)
        if score5:
            lines.append("## Strongest recreation angles (judged 5/5, highest likes)\n")
            for r in score5[:10]:
                angle = (r.get("recreation_angle") or "")[:157] + ("..." if len(r.get("recreation_angle") or "") > 160 else "")
                lines.append(f"- **[5]** {r.get('title') or r.get('caption', '')[:50]} -- "
                              f"@{r.get('creator_handle', '')} . {r.get('likes_int', '')} likes "
                              f"[{r.get('format_template', '')}/{r.get('theme', '')}]")
                lines.append(f"    -> {angle}")
            lines.append("")
        if weak:
            lines.append(f"## Weak angles to rework ({len(weak)} reels judged <=2/5)\n")
            for r in weak[:10]:
                critique = (r.get("angle_critique") or "")[:117] + ("..." if len(r.get("angle_critique") or "") > 120 else "")
                lines.append(f"- {r.get('title') or r.get('caption', '')[:50]}: {critique}")
            lines.append("")

    top_liked = sorted(vid, key=lambda r: as_int(r.get("likes_int") or r.get("likes", "")), reverse=True)[:10]
    lines.append("## Highest-engagement saves (top 10 by likes)\n")
    for r in top_liked:
        likes = r.get("likes_int") or r.get("likes", "")
        lines.append(f"- **{likes}** . {r.get('title') or r.get('caption', '')[:50]} -- "
                      f"@{r.get('creator_handle', '')} [{r.get('format_template', '')}/{r.get('theme', '')}] "
                      f"({r.get('collection', '')})")
    lines.append("")

    lines.append("## How to use this\n")
    lines.append("1. Generate ideas in your top formats x top themes above -- these combos are your strongest signal.")
    lines.append("2. Lead with your dominant hook types; they cover most of what you actually save.")
    lines.append("3. Reuse recurring named sounds from the audio identity section for proven resonance.")
    lines.append("4. Multi-save items (saved to 2+ collections, if you ran a combined build) are the strongest signal -- study those first.")
    lines.append("5. Tag `Liked?` / `Recreate?` in the vault to sharpen this profile into a personalised v2, then re-run.")
    lines.append("")

    out_path = os.path.join(base, args.out)
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))
    print(f"Wrote {out_path}  (video reels: {N})")

    fmt_present = sum(1 for r in vid if (r.get("format_template") or "").strip())
    theme_present = sum(1 for r in vid if (r.get("theme") or "").strip())
    print(f"format labels present: {fmt_present}/{N}")
    print(f"theme labels present: {theme_present}/{N}")


if __name__ == "__main__":
    main()
