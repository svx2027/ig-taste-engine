#!/bin/bash
# Resumable download queue over every feed-<slug>.json in the data dir (skips
# already-downloaded mp4s). Safe to run alongside an in-flight stream: yt-dlp
# uses .part files, so a file that shows up as done is always complete.
#
# Usage: ./run_downloads.sh [data_dir]
set -e
DATA_DIR="${1:-data}"
PY="${PYTHON:-python3}"

for f in "$DATA_DIR"/feed-*.json; do
  [ -e "$f" ] || continue
  "$PY" dl_feed.py "$f" --data-dir "$DATA_DIR"
done

touch "$DATA_DIR/.DOWNLOADS_DONE"
echo "ALL_DOWNLOADS_DONE"
