#!/usr/bin/env python3
"""
PostToolUse hook: after a REVIEW_NOTE.md write succeeds, append a
structured line to reports/audit-log.jsonl with the verdict and finding
counts by severity. This is the data source for the verdict-consistency
metric (repeat the same spec through the pipeline N times and check how
often the logged verdict matches) and gives the committee a plain audit
trail independent of the prose report.

finding_counts counts OPEN findings only, because those are what the
verdict policy table reads. Resolved findings are reported separately as
resolved_count. Counting resolved findings in finding_counts made a log
line read 'verdict APPROVE, blocker 1', which looks like a violation of
the verdict policy when it is a resolved finding behaving correctly.

Severity and status are normalized the same way block_approve_with_blocker.py
normalizes them, so the log and the enforcement agree on what 'blocker' and
'open' mean.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

VERDICT_LINE_RE = re.compile(r"\*\*Verdict:\*\*\s*(APPROVE|REVISE|RETURN)")


def norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        sys.exit(0)

    if not isinstance(payload, dict):
        sys.exit(0)

    if payload.get("tool_name") not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path") or ""
    content = tool_input.get("content") or tool_input.get("new_string") or ""

    if os.path.basename(file_path) != "REVIEW_NOTE.md":
        sys.exit(0)

    matches = VERDICT_LINE_RE.findall(content)
    verdict = matches[0] if matches else "UNKNOWN"

    course_dir = os.path.dirname(file_path)
    course_code = os.path.basename(course_dir)
    findings_path = os.path.join(course_dir, "findings.json")

    counts = {"blocker": 0, "major": 0, "minor": 0}
    resolved_count = 0
    if os.path.isfile(findings_path):
        try:
            with open(findings_path, "r", encoding="utf-8") as f:
                findings = json.load(f)
            if isinstance(findings, list):
                for finding in findings:
                    if not isinstance(finding, dict):
                        continue
                    if norm(finding.get("status")) == "resolved":
                        resolved_count += 1
                        continue
                    sev = norm(finding.get("severity"))
                    if sev in counts:
                        counts[sev] += 1
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            pass

    reports_root = os.path.dirname(course_dir)
    log_path = os.path.join(reports_root, "audit-log.jsonl")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": payload.get("session_id"),
        "course_code": course_code,
        "verdict": verdict,
        "finding_counts": counts,
        "resolved_count": resolved_count,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # logging failure must never block the pipeline

    sys.exit(0)


if __name__ == "__main__":
    main()
