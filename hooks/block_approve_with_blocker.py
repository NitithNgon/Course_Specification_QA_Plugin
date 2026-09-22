#!/usr/bin/env python3
"""
PreToolUse hook: block a Write or Edit that would land a REVIEW_NOTE.md or
COURSE_SPEC_REVIEW.md containing '**Verdict:** APPROVE' while an open
blocker-severity finding still exists in the matching findings.json.

This is the deterministic backstop described in the plugin design: skills,
commands, and agents can all be reasoned or argued out of a strict reading;
this hook cannot, because it doesn't read the agent's reasoning at all --
only the finding's severity/status fields.

Registered for both Write and Edit. A 'Write' matcher does not cover Edit,
so without the Edit branch an agent could land a correct verdict and then
edit it to APPROVE with no enforcement.

Severity and status are compared case-insensitively after stripping
whitespace, and any status other than 'resolved' counts as open. A finding
written as severity 'Blocker' or status 'Open' must not slip past the check.

Exit codes:
  0 - allow the write
  1 - allow, but surface a warning: an APPROVE was declared and the hook
      could not verify it (findings.json missing, unreadable, or not a
      JSON array). Non-blocking, but not silent.
  2 - block the write; stderr is surfaced to the model as the reason
"""
import json
import os
import re
import sys

VERDICT_LINE_RE = re.compile(r"\*\*Verdict:\*\*\s*(APPROVE|REVISE|RETURN)")
TABLE_ROW_RE = re.compile(r"^\|\s*([^\|]+?)\s*\|.*\|\s*(APPROVE|REVISE|RETURN)\s*\|", re.MULTILINE)

# Sentinel distinguishing "verified, no open blockers" (empty list) from
# "could not verify" (UNVERIFIABLE). Both allow the write, but only the
# second one warns.
UNVERIFIABLE = object()


def norm(value):
    """Lowercase and strip a field that agents author by hand."""
    if value is None:
        return ""
    return str(value).strip().lower()


def load_open_blockers(findings_path):
    if not os.path.isfile(findings_path):
        return UNVERIFIABLE
    try:
        with open(findings_path, "r", encoding="utf-8") as f:
            findings = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return UNVERIFIABLE
    if not isinstance(findings, list):
        return UNVERIFIABLE

    open_blockers = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if norm(finding.get("severity")) != "blocker":
            continue
        # Anything that is not an explicit 'resolved' counts as open, so a
        # missing, empty, or oddly-cased status fails safe toward blocking.
        if norm(finding.get("status")) == "resolved":
            continue
        open_blockers.append(finding)
    return open_blockers


def declares_approve(content):
    """True if any verdict line in the content says APPROVE.

    Checks every match rather than the first, so a note carrying both a
    RETURN and an APPROVE line is still caught.
    """
    return "APPROVE" in VERDICT_LINE_RE.findall(content)


def extract_content(tool_name, tool_input):
    """The text this call would land. Write carries the whole file; Edit
    carries only the replacement text, which is where a flipped verdict
    line would appear."""
    if tool_name == "Write":
        return tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return tool_input.get("new_string", "") or ""
    return ""


def block(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def warn(reason):
    sys.stderr.write(reason + "\n")
    sys.exit(1)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        sys.exit(0)  # can't parse input -- fail open, don't break unrelated writes

    # Valid JSON that is not an object would otherwise raise AttributeError
    # on .get() and exit 1 with a traceback in the transcript.
    if not isinstance(payload, dict):
        sys.exit(0)

    tool_name = payload.get("tool_name")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path") or ""
    content = extract_content(tool_name, tool_input)
    basename = os.path.basename(file_path)

    if basename == "REVIEW_NOTE.md":
        if not declares_approve(content):
            sys.exit(0)
        course_dir = os.path.dirname(file_path)
        findings_path = os.path.join(course_dir, "findings.json")
        open_blockers = load_open_blockers(findings_path)
        if open_blockers is UNVERIFIABLE:
            warn(
                f"Warning: {basename} declares Verdict: APPROVE but the hook "
                f"could not verify it -- {findings_path} is missing, unreadable, "
                f"or not a JSON array. The write was allowed. Confirm the "
                f"findings file was produced before the review note."
            )
        if open_blockers:
            ids = ", ".join(str(f.get("id", "?")) for f in open_blockers)
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
        unverified = []
        for course_code, verdict in TABLE_ROW_RE.findall(content):
            course_code = course_code.strip()
            if verdict != "APPROVE":
                continue
            findings_path = os.path.join(reports_root, course_code, "findings.json")
            open_blockers = load_open_blockers(findings_path)
            if open_blockers is UNVERIFIABLE:
                unverified.append(course_code)
            elif open_blockers:
                problems.append(f"{course_code} ({len(open_blockers)} open blocker(s))")
        if problems:
            block(
                "Blocked: COURSE_SPEC_REVIEW.md marks the following course(s) "
                "APPROVE despite open blocker findings: " + "; ".join(problems)
            )
        if unverified:
            warn(
                "Warning: COURSE_SPEC_REVIEW.md marks the following course(s) "
                "APPROVE but the hook could not verify them (findings.json "
                "missing, unreadable, or not a JSON array): "
                + "; ".join(unverified) + ". The write was allowed."
            )
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
