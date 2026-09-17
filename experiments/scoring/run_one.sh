#!/usr/bin/env bash
# Usage: run_one.sh <take_dir> <prompt_text_or_-> <output_dir> [--resume <session_id>]
set -euo pipefail
TAKE_DIR="$1"
PROMPT="$2"
OUT_DIR="$3"
shift 3
EXTRA_ARGS=("$@")

mkdir -p "$OUT_DIR"
TRANSCRIPT="$OUT_DIR/transcript.jsonl"

( cd "$TAKE_DIR" && claude -p "$PROMPT" \
    --model claude-sonnet-5 \
    --permission-mode bypassPermissions \
    --output-format stream-json --verbose \
    "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}" ) > "$TRANSCRIPT" 2> "$OUT_DIR/stderr.log"

python3 - "$TRANSCRIPT" "$OUT_DIR/output.json" << 'PYEOF'
import json, sys
transcript_path, out_path = sys.argv[1], sys.argv[2]
with open(transcript_path) as f:
    lines = [json.loads(l) for l in f if l.strip()]
result = next((l for l in reversed(lines) if l.get("type") == "result"), None)
with open(out_path, "w") as f:
    json.dump(result, f, indent=2)
print("session_id:", result.get("session_id") if result else None)
print("verdict text tail:", (result.get("result","")[-200:] if result else None))
PYEOF
