#!/usr/bin/env python3
"""Montage thumbnails into labeled grids for fast on-screen-text review.

Usage: python3 montage_thumbs.py <collection_slug> <sc1> <sc2> ... [--data-dir DATA_DIR]

Writes /tmp/montage_<slug>_<n>.png (6 tiles each, 3 cols x 2 rows), each tile
labeled with its shortcode.
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

TILE_W, COLS, ROWS = 460, 3, 2
PER = COLS * ROWS
LABEL_H = 30


def load_font():
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, 22)
        except Exception:
            continue
    return ImageFont.load_default()


def tile(base_dir, sc, font):
    p = f"{base_dir}/{sc}.jpg"
    if not os.path.exists(p):
        img = Image.new("RGB", (TILE_W, int(TILE_W * 16 / 9)), (40, 40, 40))
    else:
        im = Image.open(p).convert("RGB")
        h = int(TILE_W * im.height / im.width)
        img = im.resize((TILE_W, h))
    canvas = Image.new("RGB", (TILE_W, img.height + LABEL_H), (0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.text((6, 4), sc, fill=(0, 255, 120), font=font)
    canvas.paste(img, (0, LABEL_H))
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("collection")
    ap.add_argument("shortcodes", nargs="+")
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    base_dir = os.path.join(args.data_dir, "thumbnails", args.collection)
    font = load_font()

    out_files = []
    for gi in range(0, len(args.shortcodes), PER):
        group = args.shortcodes[gi:gi + PER]
        tiles = [tile(base_dir, sc, font) for sc in group]
        tile_h = max(t.height for t in tiles)
        grid = Image.new("RGB", (TILE_W * COLS, tile_h * ROWS), (10, 10, 10))
        for idx, t in enumerate(tiles):
            r, c = divmod(idx, COLS)
            grid.paste(t, (c * TILE_W, r * tile_h))
        out = f"/tmp/montage_{args.collection}_{gi // PER + 1}.png"
        grid.save(out, quality=90)
        out_files.append(out)
    print("\n".join(out_files))


if __name__ == "__main__":
    main()
