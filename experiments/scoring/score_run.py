#!/usr/bin/env python3
"""
Score one experiment run against gold-labels.json.

A "run" is the output of one `claude -p ... --output-format json` invocation,
saved as experiments/runs/<take>/<case>/output.json, optionally alongside a
copy of that Take's reports/<COURSE_CODE>/ directory (present only for Takes
that include the course-reviewer/curriculum-auditor/verdict-writer agents).

This script is deliberately defensive about the exact `--output-format json`
schema: field names below reflect the documented CLI schema as of this
plugin's authoring, but MUST be spot-checked against one real saved
output.json before the aggregated numbers are trusted (see README.md
"Known unknowns"). Never fed gold labels to the model under test -- this
script only ever runs after the fact, on saved output.

Usage:
    python experiments/scoring/score_run.py <run_dir> <course_code>

Example:
    python experiments/scoring/score_run.py \\
        experiments/runs/take4_full/clean CPE201
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_PATH = REPO_ROOT / "experiments" / "gold" / "gold-labels.json"

VERDICT_RE = re.compile(r"Verdict:\s*(APPROVE|REVISE|RETURN)", re.IGNORECASE)
FINDING_LINE_RE = re.compile(
    r"^\s*[-*]?\s*(?:\*\*)?(blocker|major|minor)(?:\*\*)?\s*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
HOOK_DENIAL_MARKERS = (
    "Blocked:",  # stderr text our own hooks emit on exit code 2
    "PreToolUse",
    "hook",
)


def load_gold(course_code: str) -> dict:
    with GOLD_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    for case in data["cases"]:
        if case["course_code"] == course_code:
            return case
    raise KeyError(f"{course_code} not found in {GOLD_PATH}")


def load_run_output(run_dir: Path) -> dict:
    output_path = run_dir / "output.json"
    with output_path.open(encoding="utf-8") as f:
        return json.load(f)


def extract_verdict(result_text: str):
    matches = VERDICT_RE.findall(result_text)
    return matches[-1].upper() if matches else None


def extract_findings(result_text: str):
    return [
        {"severity": sev.lower(), "text": text.strip()}
        for sev, text in FINDING_LINE_RE.findall(result_text)
    ]


def count_agent_calls(transcript_events: list) -> int:
    """Counts Task tool_use blocks (subagent invocations) in a stream-json transcript."""
    return sum(
        1
        for e in transcript_events
        if e.get("type") == "assistant"
        for block in e.get("message", {}).get("content", [])
        if block.get("type") == "tool_use" and block.get("name") == "Task"
    )


def count_skill_calls(transcript_events: list) -> int:
    return sum(
        1
        for e in transcript_events
        if e.get("type") == "assistant"
        for block in e.get("message", {}).get("content", [])
        if block.get("type") == "tool_use" and block.get("name") == "Skill"
    )


def detect_hook_block(transcript_events: list) -> bool:
    for e in transcript_events:
        blob = json.dumps(e)
        if "exit code 2" in blob or "PreToolUse" in blob and "Blocked:" in blob:
            return True
    return False


def score(run_dir: Path, course_code: str):
    gold = load_gold(course_code)
    output = load_run_output(run_dir)

    result_text = output.get("result", "")
    model_verdict = extract_verdict(result_text)
    findings = extract_findings(result_text)

    transcript_path = run_dir / "transcript.jsonl"
    transcript_events = []
    if transcript_path.exists():
        with transcript_path.open(encoding="utf-8") as f:
            transcript_events = [json.loads(line) for line in f if line.strip()]

    report = {
        "course_code": course_code,
        "category": gold["category"],
        "expected_verdict": gold["expected_verdict"],
        "model_verdict": model_verdict,
        "verdict_match": model_verdict == gold["expected_verdict"],
        "num_findings": len(findings),
        "findings_by_severity": {
            sev: sum(1 for f in findings if f["severity"] == sev)
            for sev in ("blocker", "major", "minor")
        },
        "false_blocker": (
            gold["category"] == "clean"
            and findings_by_severity_has_blocker(findings)
        ),
        "agent_calls": count_agent_calls(transcript_events),
        "skill_calls": count_skill_calls(transcript_events),
        "hook_block_detected": detect_hook_block(transcript_events),
        "duration_ms": output.get("duration_ms"),
        "total_cost_usd": output.get("total_cost_usd"),
        "num_turns": output.get("num_turns"),
    }
    return report


def findings_by_severity_has_blocker(findings):
    return any(f["severity"] == "blocker" for f in findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("course_code")
    args = parser.parse_args()

    report = score(args.run_dir, args.course_code)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
