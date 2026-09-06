#!/usr/bin/env python3
"""Capture just the Chrome window currently showing Instagram, to a PNG (macOS only).

Usage: python3 capture_page.py <output_path.png>

Finds the on-screen Google Chrome window whose title looks like Instagram, then
`screencapture -l<windowid>` grabs that window only (ignores anything overlapping
it). Prints the chosen window title + path, or NOFOUND.

Deliberately refuses rather than falling back to another window: Chrome-MCP-style
screenshots never persist to local disk, and `screencapture -l<winid>` only
renders a window that is on the active macOS Space, so silently grabbing "some
Chrome window" risks capturing an unrelated tab instead of Instagram.
"""
import sys
import subprocess
import Quartz


def main():
    if len(sys.argv) < 2:
        print("usage: python3 capture_page.py <output_path.png>", file=sys.stderr)
        sys.exit(1)
    out = sys.argv[1]

    wins = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    cands = []
    for w in wins:
        if w.get("kCGWindowOwnerName", "") not in ("Google Chrome", "Chrome"):
            continue
        b = w["kCGWindowBounds"]
        area = b["Width"] * b["Height"]
        title = w.get("kCGWindowName", "") or ""
        cands.append((area, w["kCGWindowNumber"], title))

    # ONLY capture an on-screen Instagram window. Never fall back to another
    # tab/window (that would silently grab something unrelated). If none is on
    # the active Space -> NOFOUND.
    ig = [c for c in cands if "instagram" in c[2].lower()]
    pick = max(ig, key=lambda c: c[0]) if ig else None
    if not pick:
        print("NOFOUND (no on-screen Instagram window on the active Space)")
        sys.exit(2)

    wid = pick[1]
    subprocess.run(["screencapture", f"-l{wid}", "-o", "-x", out], check=True)
    print(f"OK wid={wid} title={pick[2][:50]!r} -> {out}")


if __name__ == "__main__":
    main()
