"""Completion checks: the "verify" before the agent loop accepts a final answer (M8), and the
read-only checks of the VERIFY state (M9).

Each check takes a spec path and returns what is still missing (one sentence the model can
act on), or None when the stage's work is done. They only read: the spec, the rulebook and
reports/<code>/. A stage is done when every finding its rule checks produce is in
findings.json, so a model that answers before recording (stops too early) is caught here.
"""
from __future__ import annotations

import re

from . import data_store as ds
from . import qa_rules as rules
from .qa_tools import SCOPE_OWNER, _code, _drafts, _load, _overrides


def _unrecorded(path: str, check: str) -> list[str]:
    """Rules whose draft findings for `check` are not yet in findings.json."""
    spec, p = _load(path)
    have = {(f["checklist_rule"], f["section"], f["quote"]) for f in ds.load_findings(_code(spec, p))}
    return sorted({d["checklist_rule"] for d in _drafts(spec, p, check)
                   if d["source_agent"] == SCOPE_OWNER[check]
                   and (d["checklist_rule"], d["section"], d["quote"]) not in have})


def reviewer_done(path: str) -> str | None:
    spec, p = _load(path)
    if not ds.findings_path(_code(spec, p)).is_file():
        return 'findings.json does not exist yet: call record_check_results with check="structure".'
    if miss := _unrecorded(path, "structure"):
        return f'findings for rules {miss} are not recorded: call record_check_results with check="structure".'
    return None


def auditor_done(path: str) -> str | None:
    spec, p = _load(path)
    lv = rules.clo_levels(spec, _overrides(_code(spec, p)))
    pending = [c.id for c in spec.clos if not lv[c.id]["classifiable"] and not lv[c.id].get("override")]
    if pending:
        return f"{pending} have no classified student verb: decide each and call set_clo_level."
    todo = [f'check="{c}" (rules {miss})' for c in ("bloom", "plo") if (miss := _unrecorded(path, c))]
    if todo:
        return "call record_check_results with " + " and with ".join(todo) + "."
    return None


def writer_done(path: str) -> str | None:
    spec, p = _load(path)
    code = _code(spec, p)
    note = ds.course_dir(code) / "REVIEW_NOTE.md"
    if not note.is_file():
        return f'REVIEW_NOTE.md is not written: call write_review_note with course_code="{code}".'
    m = re.search(r"\*\*Verdict:\*\* (\w+)", note.read_text(encoding="utf-8"))
    if not m or m[1] != rules.compute_verdict(ds.load_findings(code))["verdict"]:
        return "REVIEW_NOTE.md is older than findings.json: call write_review_note again."
    return None


CHECKS = {"course-reviewer": reviewer_done, "curriculum-auditor": auditor_done, "verdict-writer": writer_done}
