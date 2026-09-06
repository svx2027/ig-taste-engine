#!/bin/bash
# Incrementally extract frames + transcribe as downloads land (run_downloads.sh
# in another terminal), then do one final pass once .DOWNLOADS_DONE appears.
# Resumable: both frames.py and whisper_transcribe.py skip clips already done,
# so re-running this after an interruption costs nothing.
#
# Usage: ./run_offline.sh [data_dir]
set -e
DATA_DIR="${1:-data}"
PY="${PYTHON:-python3}"
MARK="$DATA_DIR/.DOWNLOADS_DONE"

pass=0
while [ ! -f "$MARK" ]; do
  pass=$((pass + 1))
  echo "=== incremental pass $pass ==="
  "$PY" frames.py --data-dir "$DATA_DIR"
  "$PY" whisper_transcribe.py --data-dir "$DATA_DIR"
  sleep 20
done

echo "=== downloads done; final offline pass ==="
"$PY" frames.py --data-dir "$DATA_DIR"
"$PY" whisper_transcribe.py --data-dir "$DATA_DIR"
touch "$DATA_DIR/.OFFLINE_DONE"
echo "OFFLINE_DONE"
