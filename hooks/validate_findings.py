#!/usr/bin/env python3
"""
PreToolUse hook: validate a Write or Edit to any findings.json against
references/checklist.md before it lands.

The rulebook says every finding carries the checklist's severity for its
rule, comes from the agent that owns the rule, and is never deleted or
rewritten once written. Agents can be argued out of instructions; this hook
reads only the resulting file, so it holds those rules regardless of the
reasoning that produced the write.

Blocks (exit 2) when the file that would result from the call:
  - is not a JSON array of objects;
  - has a finding with a missing or empty required field;
  - repeats a finding id;
  - cites a checklist_rule that is not a rule row in checklist.md;
  - gives a severity different from that rule's severity;
  - gives a source_agent different from that rule's owner;
  - has a status other than open or resolved, or is resolved without a
    resolution_note;
  - drops a finding the current file has, or changes its checklist_rule,
    severity, source_agent, section or quote.

Only status and resolution_note may change on an existing finding.

Calls whose target is not a reports/<course_code>/findings.json pass
untouched, so a findings.json elsewhere is never judged by this rulebook. If
checklist.md cannot be read or has no rule rows, findings.json writes are
blocked: validating against an empty rulebook would let any severity
through.

The checklist path defaults to ../references/checklist.md next to this
script; the COURSE_SPEC_QA_CHECKLIST environment variable overrides it.
log_verdict.py resolves the path the same way.
"""
import json
import os
import re
import sys

REQUIRED_FIELDS = (
    "id", "source_agent", "checklist_rule", "severity",
    "section", "quote", "message", "suggested_fix", "status",
)
IMMUTABLE_FIELDS = ("checklist_rule", "severity", "source_agent", "section", "quote")
SEVERITIES = {"blocker", "major", "minor"}
STATUSES = {"open", "resolved"}
RULE_ID_RE = re.compile(r"^(?:[A-Z]\.\d+|\d+\.\d+)$")
MAX_REPORTED = 20


def norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def is_course_findings(path):
    """True for .../reports/<course_code>/findings.json, with / or \\ separators, on any OS."""
    parts = re.split(r"[\\/]", path or "")
    return len(parts) >= 3 and parts[-1] == "findings.json" and parts[-3] == "reports"


def checklist_path():
    override = os.environ.get("COURSE_SPEC_QA_CHECKLIST")
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "references", "checklist.md")


def load_rules(path):
    """Map rule id -> (severity, owner) from the checklist's rule table.

    A rule row is a table row whose first cell is a rule id. Severity and
    owner are read from the last two cells, so a '|' inside the Check text
    cannot shift them.
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return {}
    rules = {}
    for line in lines:
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or not RULE_ID_RE.match(cells[0]):
            continue
        severity, owner = norm(cells[-2]), norm(cells[-1])
        if severity in SEVERITIES and owner:
            rules[cells[0]] = (severity, owner)
    return rules


def parse_findings(text):
    """(list, None) for a JSON array of objects, else (None, reason)."""
    try:
        data = json.loads(text.lstrip("﻿"))
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON ({exc.msg} at line {exc.lineno})"
    if not isinstance(data, list):
        return None, "the top level must be a JSON array of findings"
    if not all(isinstance(item, dict) for item in data):
        return None, "every entry must be a JSON object"
    return data, None


def check_findings(findings, rules):
    problems = []
    seen = set()
    for index, finding in enumerate(findings):
        label = str(finding.get("id") or f"entry {index}")
        missing = [k for k in REQUIRED_FIELDS if norm(finding.get(k)) == ""]
        if missing:
            problems.append(f"{label}: missing or empty field(s): {', '.join(missing)}")
            continue
        fid = str(finding["id"]).strip()
        if fid in seen:
            problems.append(f"{label}: duplicate id")
        seen.add(fid)
        rule = str(finding["checklist_rule"]).strip()
        if rule not in rules:
            problems.append(f"{label}: checklist_rule '{rule}' is not a rule in checklist.md")
            continue
        severity, owner = rules[rule]
        if norm(finding["severity"]) != severity:
            problems.append(f"{label}: rule {rule} has severity '{severity}' in checklist.md, "
                            f"not '{finding['severity']}'")
        if norm(finding["source_agent"]) != owner:
            problems.append(f"{label}: rule {rule} is owned by '{owner}', "
                            f"not '{finding['source_agent']}'")
        status = norm(finding["status"])
        if status not in STATUSES:
            problems.append(f"{label}: status must be 'open' or 'resolved', not '{finding['status']}'")
        elif status == "resolved" and norm(finding.get("resolution_note")) == "":
            problems.append(f"{label}: a resolved finding needs a resolution_note")
    return problems


def check_append_only(old, new):
    problems = []
    new_by_id = {str(f.get("id")).strip(): f for f in new}
    for finding in old:
        fid = str(finding.get("id")).strip()
        if fid not in new_by_id:
            problems.append(f"{fid}: an existing finding was removed; "
                            f"mark it resolved with a resolution_note instead")
            continue
        for field in IMMUTABLE_FIELDS:
            if norm(finding.get(field)) != norm(new_by_id[fid].get(field)):
                problems.append(f"{fid}: '{field}' of an existing finding cannot change")
    return problems


def read_current(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def resulting_content(tool_name, tool_input, current):
    """Text the file holds after the call, or None when the call will fail anyway."""
    if tool_name == "Write":
        return tool_input.get("content") or ""
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if current is None or old is None or new is None or old not in current:
        return None
    if tool_input.get("replace_all"):
        return current.replace(old, new)
    return current.replace(old, new, 1)


def block(problems):
    shown = problems[:MAX_REPORTED]
    more = len(problems) - len(shown)
    sys.stderr.write("Blocked: findings.json would break the rulebook:\n- " + "\n- ".join(shown)
                     + (f"\n({more} more)" if more else "") + "\n")
    sys.exit(2)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    tool_name, tool_input = payload.get("tool_name"), payload.get("tool_input")
    if tool_name not in ("Write", "Edit") or not isinstance(tool_input, dict):
        sys.exit(0)
    path = tool_input.get("file_path") or ""
    if not is_course_findings(path):
        sys.exit(0)

    rules = load_rules(checklist_path())
    if not rules:
        block([f"checklist.md could not be read or has no rule rows ({checklist_path()})"])

    current = read_current(path)
    content = resulting_content(tool_name, tool_input, current)
    if content is None:
        sys.exit(0)

    findings, reason = parse_findings(content)
    if findings is None:
        block([reason])
    problems = check_findings(findings, rules)
    if current is not None:
        old, _ = parse_findings(current)
        if old is not None:
            problems += check_append_only(old, findings)
    if problems:
        block(problems)
    sys.exit(0)


if __name__ == "__main__":
    main()
