#!/usr/bin/env python3
"""
PostToolUse hook: after a REVIEW_NOTE.md write succeeds, append a
structured line to reports/audit-log.jsonl with the verdict and finding
counts by severity. This is the data source for the verdict-consistency
metric (repeat the same spec through the pipeline N times and check how
often the logged verdict matches) and gives the committee a plain audit
trail independent of the prose report.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

VERDICT_LINE_RE = re.compile(r"\*\*Verdict:\*\*\s*(APPROVE|REVISE|RETURN)")


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if payload.get("tool_name") != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if os.path.basename(file_path) != "REVIEW_NOTE.md":
        sys.exit(0)

    m = VERDICT_LINE_RE.search(content)
    verdict = m.group(1) if m else "UNKNOWN"

    course_dir = os.path.dirname(file_path)
    course_code = os.path.basename(course_dir)
    findings_path = os.path.join(course_dir, "findings.json")

    counts = {"blocker": 0, "major": 0, "minor": 0}
    if os.path.isfile(findings_path):
        try:
            with open(findings_path, "r", encoding="utf-8") as f:
                findings = json.load(f)
            for finding in findings:
                sev = finding.get("severity")
                if sev in counts:
                    counts[sev] += 1
        except (json.JSONDecodeError, OSError):
            pass

    reports_root = os.path.dirname(course_dir)
    log_path = os.path.join(reports_root, "audit-log.jsonl")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": payload.get("session_id"),
        "course_code": course_code,
        "verdict": verdict,
        "finding_counts": counts,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # logging failure must never block the pipeline

    sys.exit(0)


if __name__ == "__main__":
    main()
