"""Show the QA tools on one spec, and how the executor and the plugin's validator reject bad calls.

    python scripts/demo_qa_tools.py                         # tools on CPE501 (three Bloom defects)
    python scripts/demo_qa_tools.py courses/CPE430.md
    python scripts/demo_qa_tools.py --failure               # the plugin's guarantees, as tool errors

Runs in a scratch copy of the plugin (without evaluation/), so reports/ is untouched. No Ollama needed.
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

import _path  # noqa: F401

from harness import Harness, data_store as ds, execute
from harness import qa_tools  # noqa: F401  (registers the tools)


def sandbox() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="qa_demo_"))
    for d in ("courses", "references", "hooks"):
        shutil.copytree(ds.root() / d, tmp / d, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    ds.configure(tmp)
    return tmp


def call(h, name, args, allowed=frozenset({"read"}), width=1400):
    out = execute({"function": {"name": name, "arguments": args}}, allowed=set(allowed),
                  logger=h.log, run_id="qa-demo")
    print(f"\n> {name}({json.dumps(args, ensure_ascii=False)})\n"
          f"{json.dumps(out, indent=1, ensure_ascii=False)[:width]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="courses/CPE501.md")
    ap.add_argument("--failure", action="store_true")
    a = ap.parse_args()
    tmp = sandbox()
    h = Harness(log_file=tmp / "calls.jsonl")
    RW = {"read", "write"}
    if not a.failure:
        call(h, "check_form_gate", {"path": a.path})
        call(h, "check_weights", {"path": a.path})
        call(h, "derive_clo_levels", {"path": a.path})
        call(h, "run_reviewer_checks", {"path": a.path})
        call(h, "run_bloom_checks", {"path": a.path})
        call(h, "run_plo_checks", {"path": a.path})
        print(f"\n(scratch root: {tmp})")
        return

    p = "courses/CPE502.md"
    call(h, "record_check_results", {"path": p, "check": "structure"}, RW, 600)   # 4.3 blocker: sum 95
    print("\n--- calls a small model might make ---")
    call(h, "get_verdict_for", {"course_code": "CPE502"}, width=300)            # made-up tool
    call(h, "check_weights", {"file": p}, width=300)                            # wrong argument name
    call(h, "read_course_spec", {"path": "evaluation/CPE502.md"})               # the answers
    call(h, "read_course_spec", {"path": "../../secrets.md"})                   # outside the plugin
    call(h, "add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                            "checklist_rule": "4.7", "section": "Assessment table, row \"Final project\"",
                            "quote": "| Final project |", "message": "level looks too high",
                            "suggested_fix": "lower the level"}, RW)            # rule owned by the auditor
    call(h, "add_finding", {"course_code": "CPE502", "source_agent": "curriculum-auditor",
                            "checklist_rule": "2.7", "section": "Course learning outcomes, row \"CLO4\"",
                            "quote": "| CLO4 |", "message": "licensing mapped to ethics",
                            "suggested_fix": "check the mapping"}, RW)          # no citation
    call(h, "add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                            "checklist_rule": "4.3", "severity": "minor", "section": "Assessment table",
                            "quote": "Total 95", "message": "rounding, ignore",
                            "suggested_fix": "none needed"}, RW)                # severity is not an input
    call(h, "resolve_finding", {"course_code": "CPE502", "finding_id": "F001",
                                "resolution_note": "owner says participation makes it 100",
                                "resolved_by": "agent"}, RW)                    # needs 'dangerous'
    call(h, "write_review_note", {"course_code": "CPE502", "spec_path": p, "verdict": "APPROVE"}, RW)

    print("\n--- a direct edit of findings.json, checked by the plugin's hooks/validate_findings.py ---")
    f = ds.load_findings("CPE502")
    try:
        ds.save_findings("CPE502", [{**f[0], "severity": "minor"}])
    except ValueError as e:
        print(e)
    try:
        ds.save_findings("CPE502", [])
    except ValueError as e:
        print(e)

    call(h, "write_review_note", {"course_code": "CPE502", "spec_path": p}, RW)
    note = (tmp / "reports" / "CPE502" / "REVIEW_NOTE.md").read_text(encoding="utf-8")
    print("\nVerdict line in the written note:", [l for l in note.splitlines() if "Verdict" in l])


if __name__ == "__main__":
    main()
