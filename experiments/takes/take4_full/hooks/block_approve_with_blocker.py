#!/usr/bin/env python3
"""
PreToolUse hook: block a Write call that would land a REVIEW_NOTE.md or
COURSE_SPEC_REVIEW.md containing '**Verdict:** APPROVE' while an open
blocker-severity finding still exists in the matching findings.json.

This is the deterministic backstop described in the plugin design: skills,
commands, and agents can all be reasoned or argued out of a strict reading;
this hook cannot, because it doesn't read the agent's reasoning at all --
only the finding's severity/status fields.

Exit codes:
  0 - allow the write
  2 - block the write; stderr is surfaced to the model as the reason
"""
import json
import os
import re
import sys

VERDICT_LINE_RE = re.compile(r"\*\*Verdict:\*\*\s*(APPROVE|REVISE|RETURN)")
TABLE_ROW_RE = re.compile(r"^\|\s*([^\|]+?)\s*\|.*\|\s*(APPROVE|REVISE|RETURN)\s*\|", re.MULTILINE)


def load_open_blockers(findings_path):
    if not os.path.isfile(findings_path):
        return None  # no findings file at all -- can't verify, caller decides
    try:
        with open(findings_path, "r", encoding="utf-8") as f:
            findings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return [
        f for f in findings
        if f.get("severity") == "blocker" and f.get("status", "open") == "open"
    ]


def block(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # can't parse input -- fail open, don't break unrelated writes

    if payload.get("tool_name") != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")
    basename = os.path.basename(file_path)

    if basename == "REVIEW_NOTE.md":
        m = VERDICT_LINE_RE.search(content)
        if not m or m.group(1) != "APPROVE":
            sys.exit(0)
        course_dir = os.path.dirname(file_path)
        findings_path = os.path.join(course_dir, "findings.json")
        open_blockers = load_open_blockers(findings_path)
        if open_blockers:
            ids = ", ".join(f.get("id", "?") for f in open_blockers)
            block(
                f"Blocked: {basename} declares Verdict: APPROVE but "
                f"{findings_path} still has {len(open_blockers)} open "
                f"blocker finding(s) ({ids}). Resolve or downgrade these "
                f"findings first, or write REVISE/RETURN instead."
            )
        sys.exit(0)

    if basename == "COURSE_SPEC_REVIEW.md":
        reports_root = os.path.dirname(file_path)  # reports/
        problems = []
        for course_code, verdict in TABLE_ROW_RE.findall(content):
            course_code = course_code.strip()
            if verdict != "APPROVE":
                continue
            findings_path = os.path.join(reports_root, course_code, "findings.json")
            open_blockers = load_open_blockers(findings_path)
            if open_blockers:
                problems.append(f"{course_code} ({len(open_blockers)} open blocker(s))")
        if problems:
            block(
                "Blocked: COURSE_SPEC_REVIEW.md marks the following course(s) "
                "APPROVE despite open blocker findings: " + "; ".join(problems)
            )
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
