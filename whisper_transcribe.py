#!/usr/bin/env python3
"""Transcribe every downloaded reel with a local Whisper model (default: mlx-whisper
large-v3-turbo, tuned for Apple Silicon).

Resumable: skips reels whose transcript .txt already exists. Raw transcript
only; a lyrics-vs-voiceover split and confidence flags are a separate,
content-aware pass (music transcripts are unreliable — treat `audio_name` as
the trustworthy field for music, not the transcript).

Usage: python3 whisper_transcribe.py [--data-dir DATA_DIR]
                                      [--mlx-path MLX_WHISPER_BIN]
                                      [--model MODEL_ID]
"""
import argparse
import glob
import json
import os
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--mlx-path", default="mlx_whisper", help="mlx_whisper binary on PATH, or a full path")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    args = ap.parse_args()
    root = args.data_dir

    feeds = sorted(glob.glob(f"{root}/feed-*.json"))
    todo = []
    for fp in feeds:
        feed = json.load(open(fp))
        slug = feed["slug"]
        os.makedirs(f"{root}/transcripts/{slug}", exist_ok=True)
        for r in feed["reels"]:
            sc = r["code"]
            v = f"{root}/videos/{slug}/{sc}.mp4"
            txt = f"{root}/transcripts/{slug}/{sc}.txt"
            if os.path.exists(v) and not os.path.exists(txt):
                todo.append((slug, sc, v))

    print(f"to transcribe: {len(todo)}", flush=True)
    for i, (slug, sc, v) in enumerate(todo, 1):
        subprocess.run(
            [args.mlx_path, v, "--model", args.model,
             "--output-dir", f"{root}/transcripts/{slug}", "--output-format", "txt"],
            capture_output=True, text=True,
        )
        if i % 10 == 0 or i == len(todo):
            print(f"whisper {i}/{len(todo)} last={slug}/{sc}", flush=True)
    print("WHISPER_DONE", flush=True)


if __name__ == "__main__":
    main()
