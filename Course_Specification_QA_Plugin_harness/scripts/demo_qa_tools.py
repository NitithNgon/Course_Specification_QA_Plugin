"""Show each QA tool on one spec, and how the executor rejects bad or forbidden calls.

    python scripts/demo_qa_tools.py                                  # tools on CPE502 (weights = 95)
    python scripts/demo_qa_tools.py courses/blocker_03_missing_plo.md
    python scripts/demo_qa_tools.py --failure                        # the plugin's guarantees as tool errors

Runs in a scratch copy of the plugin root, so reports/ is untouched. No Ollama needed.
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
    for d in ("courses", "references"):
        shutil.copytree(ds.root() / d, tmp / d)
    ds.configure(tmp)
    return tmp


def call(h, name, args, allowed=frozenset({"read"})):
    out = execute({"function": {"name": name, "arguments": args}}, allowed=set(allowed),
                  logger=h.log, run_id="qa-demo")
    print(f"\n> {name}({json.dumps(args)})\n{json.dumps(out, indent=1, ensure_ascii=False)[:1400]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="courses/blocker_02_weight_95.md")
    ap.add_argument("--failure", action="store_true")
    a = ap.parse_args()
    tmp = sandbox()
    h = Harness()
    RW = {"read", "write"}
    if not a.failure:
        call(h, "parse_course_spec", {"path": a.path})
        call(h, "check_weights", {"path": a.path})
        call(h, "run_structure_check", {"path": a.path})
        call(h, "bloom_review", {"path": a.path})
        call(h, "run_plo_check", {"path": a.path})
        print(f"\n(scratch root: {tmp})")
        return

    p = "courses/blocker_02_weight_95.md"
    call(h, "record_check_results", {"path": p, "check": "structure"}, RW)   # CPE502 now has a blocker
    print("\n--- calls a small model might make ---")
    call(h, "get_verdict_for", {"course_code": "CPE502"})                     # made-up tool
    call(h, "check_weights", {"file": p})                                     # wrong argument name
    call(h, "read_course_spec", {"path": "../../secrets.txt"})                # path escape
    call(h, "add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                            "checklist_rule": "3.3", "severity": "minor", "section": "Section 3",
                            "quote": "Total: 95", "message": "Rounding, ignore",
                            "suggested_fix": "None needed"}, RW)              # downgrade a blocker
    call(h, "add_finding", {"course_code": "CPE502", "source_agent": "curriculum-auditor",
                            "checklist_rule": "2.4", "severity": "major", "section": "Section 2",
                            "quote": "CLO2", "message": "Verb mismatch here",
                            "suggested_fix": "Reword the verb"}, RW)          # no citation
    call(h, "resolve_finding", {"course_code": "CPE502", "finding_id": "F001",
                                "resolution_note": "owner says it is fine",
                                "resolved_by": "agent"}, RW)                  # needs 'dangerous'
    call(h, "write_review_note", {"course_code": "CPE502", "spec_path": p,
                                  "verdict": "APPROVE"}, RW)                  # verdict is not an input
    out = call(h, "write_review_note", {"course_code": "CPE502", "spec_path": p}, RW)
    note = (tmp / "reports" / "CPE502" / "REVIEW_NOTE.md").read_text(encoding="utf-8")
    print("\nVerdict line in the written note:", [l for l in note.splitlines() if "Verdict" in l])


if __name__ == "__main__":
    main()
