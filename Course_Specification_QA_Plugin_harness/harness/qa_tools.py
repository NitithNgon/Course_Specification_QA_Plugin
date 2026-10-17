"""M6 tools for the Course Specification QA pipeline. Importing registers them.

Design rule: anything with one right answer is a tool (parsing, weight sums, verb
lookup, PLO validity, verdict policy, report rendering). The model only decides what
rules cannot: which tool to call next, how to classify an unknown verb, and whether a
mapping is a poor pedagogical fit.

Permissions (checked by executor.execute(allowed=...)):
  read       - inspect specs, references, findings; run the deterministic checks
  write      - append findings, write reports. Never accepts a verdict as input
  dangerous  - resolve_finding. Human reviewers only; no agent stage is granted it

The verdict rule lives in code: `write_review_note` computes the verdict from
findings.json itself, so "APPROVE with an open blocker" cannot be expressed. That
replaces the PreToolUse hook in the Claude Code plugin; `log_verdict` is replaced by the
audit-log append inside the same tool.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import data_store as ds
from . import qa_rules as rules
from .spec_parser import Spec, parse_spec
from .tools import tool

MAX_SPEC_CHARS = 20000
SEVERITIES = ("blocker", "major", "minor")
AMENDMENT_COLS = ["course_code", "course_name", "verdict", "finding_id", "severity", "section",
                  "summary", "suggested_fix", "owner", "due_date"]


class Args(BaseModel):
    """Unknown argument names are rejected, so a model cannot slip in e.g. verdict="APPROVE"."""
    model_config = ConfigDict(extra="forbid")


def _rel(p) -> str:
    try:
        return str(p.relative_to(ds.root())).replace("\\", "/")
    except ValueError:
        return str(p)


def _spec(path: str) -> Spec:
    p = ds.resolve_spec(path)
    return parse_spec(p.read_text(encoding="utf-8"), str(p))


# =============================================================== read: documents
class NoArgs(Args):
    pass


@tool(permission="read")
def list_course_specs(args: NoArgs) -> dict:
    """List the course specification files available for review (paths relative to the plugin root)."""
    return {"specs": ds.list_specs()}


class PathArgs(Args):
    path: str = Field(description="Spec path as returned by list_course_specs, e.g. courses/clean_01_data_structures.md")


@tool(permission="read")
def read_course_spec(args: PathArgs) -> dict:
    """Return the raw text of one course specification. Use only when the parsed view is not enough."""
    text = ds.resolve_spec(args.path).read_text(encoding="utf-8")
    return {"path": args.path, "truncated": len(text) > MAX_SPEC_CHARS,
            "text": text[:MAX_SPEC_CHARS]}


@tool(permission="read")
def parse_course_spec(args: PathArgs) -> dict:
    """Extract course code, name, CLO table, assessment table, stated total, rubric and policy
    statements from a spec, verbatim. Call this first for every course."""
    s = _spec(args.path).to_dict()
    s["policies_present"] = sorted(s.pop("policies"))
    return s


@tool(permission="read")
def check_weights(args: PathArgs) -> dict:
    """Compute the exact assessment-weight sum and its delta from 100. Use instead of adding numbers yourself."""
    return rules.weight_report(_spec(args.path))


# ======================================================= read: deterministic checks
class CheckArgs(Args):
    path: str = Field(description="Spec path as returned by list_course_specs")


@tool(permission="read")
def run_structure_check(args: CheckArgs) -> dict:
    """Run checklist items 1.x, 2.1-2.3, 2.5, 3.1-3.5 and 4.x (completeness, weight sum, policies) on a spec.
    Returns draft findings with section pointers and verbatim quotes. Does not save anything."""
    drafts = rules.check_structure(_spec(args.path))
    return {"count": len(drafts), "findings": drafts}


@tool(permission="read")
def bloom_review(args: CheckArgs) -> dict:
    """Classify every CLO verb against Bloom's taxonomy and compare with the stated level.
    Status needs_model_judgment means the verb is not in the dictionary: classify it by the
    closest synonym yourself and add a finding with add_finding if it mismatches."""
    return {"clos": rules.bloom_review(_spec(args.path))}


class VerbArgs(Args):
    verb: str = Field(description="A single English verb, e.g. 'critique'")


@tool(permission="read")
def lookup_bloom_verb(args: VerbArgs) -> dict:
    """Look up one verb in the Bloom verb dictionary. Returns its level, or null if it is not listed."""
    level = rules.lookup_verb(args.verb)
    return {"verb": args.verb, "level": level,
            "note": None if level else "not in dictionary: classify by closest synonym and say it is inferred"}


@tool(permission="read")
def run_bloom_check(args: CheckArgs) -> dict:
    """Run checklist 2.4 (stated Bloom level vs verb) and 3.6 (Evaluate/Create needs a project/design/critique
    deliverable) on a spec. Returns draft findings with Bloom citations. Does not save anything."""
    drafts = rules.check_bloom(_spec(args.path))
    return {"count": len(drafts), "findings": drafts}


@tool(permission="read")
def get_plo_catalog(args: NoArgs) -> dict:
    """Return the program's PLO catalog (PLO ID to statement). Valid PLO IDs are exactly these."""
    return ds.plo_catalog()


class PloIdsArgs(Args):
    plo_ids: list[str] = Field(description="PLO IDs to validate, e.g. ['PLO1', 'PLO99']")


@tool(permission="read")
def validate_plo_ids(args: PloIdsArgs) -> dict:
    """Check PLO IDs against the catalog. Returns which are valid and which are dangling."""
    return rules.validate_plo_ids(args.plo_ids, ds.plo_catalog())


@tool(permission="read")
def run_plo_check(args: CheckArgs) -> dict:
    """Run checklist 2.5 and 2.6 (CLO without PLO, PLO ID missing from the catalog) on a spec.
    Returns draft findings. Does not save anything."""
    drafts = rules.check_plo(_spec(args.path), ds.plo_catalog())
    return {"count": len(drafts), "findings": drafts}


class CoverageArgs(Args):
    paths: list[str] = Field(description="Spec paths in this batch")


@tool(permission="read")
def plo_coverage_rollup(args: CoverageArgs) -> dict:
    """Program-level PLO coverage across a batch of specs: covered, unverified-only and uncovered PLOs."""
    return rules.plo_coverage([_spec(p) for p in args.paths], ds.plo_catalog())


# ============================================================== read: findings state
class CourseArgs(Args):
    course_code: str = Field(description="Course code, e.g. CPE201")


@tool(permission="read")
def get_findings(args: CourseArgs) -> dict:
    """Return all findings recorded so far for a course (reports/<code>/findings.json)."""
    f = ds.load_findings(args.course_code)
    return {"course_code": args.course_code, "count": len(f), "findings": f}


@tool(permission="read")
def get_verdict(args: CourseArgs) -> dict:
    """Apply the fixed verdict policy to a course's findings: RETURN if an open blocker,
    REVISE if an open major, else APPROVE. This is a lookup, not a judgment."""
    return {"course_code": args.course_code, **rules.compute_verdict(ds.load_findings(args.course_code))}


# ================================================================ write: findings
class FindingArgs(Args):
    course_code: str
    source_agent: Literal["course-reviewer", "curriculum-auditor"]
    checklist_rule: str = Field(description="Checklist item such as '2.4', or 'plo-fit' for a pedagogical-fit note")
    severity: Literal["blocker", "major", "minor"]
    section: str = Field(min_length=3, description="Where in the spec, e.g. 'Section 2 -> Learning Outcomes -> CLO2'")
    quote: str = Field(min_length=1, description="Verbatim text from the spec")
    message: str = Field(min_length=5)
    suggested_fix: str = Field(min_length=5, description="One actionable sentence")
    standard_ref: str | None = Field(default=None, description="Required for curriculum-auditor: the named standard and rule")


def _commit(course_code: str, d: dict, source_agent: str, existing: list[dict]) -> dict:
    """Validate a draft against plugin rules, then append it. Returns the stored finding."""
    rule, sev = d["checklist_rule"], d["severity"]
    if rule == "plo-fit":
        if sev != "minor":
            raise ValueError("plo-fit notes are always minor severity")
    elif rule in rules.SEVERITY:
        fixed = rules.SEVERITY[rule]
        if sev != fixed and not (rule == "2.4" and sev in ("major", "minor")):
            raise ValueError(f"Severity for rule {rule} is fixed at '{fixed}' by checklist.md. "
                             "Add your disagreement to the message; do not change the severity.")
    else:
        raise ValueError(f"Unknown checklist_rule {rule!r}. Known: {sorted(rules.SEVERITY)} + 'plo-fit'")
    if source_agent == "curriculum-auditor" and not d.get("standard_ref"):
        raise ValueError("curriculum-auditor findings must cite a standard_ref")
    for f in existing:
        if f["checklist_rule"] == rule and f["section"] == d["section"]:
            return {**f, "deduplicated": True}
    f = {"id": f"F{len(existing) + 1:03d}", "source_agent": source_agent, **d, "status": "open"}
    existing.append(f)
    return f


@tool(permission="write")
def add_finding(args: FindingArgs) -> dict:
    """Record one finding for a course. Requires a section pointer, a verbatim quote and a fix.
    Use for judgment-based findings (inferred verb level, poor PLO fit); use record_check_results
    for rule-based ones. Severity of checklist rules cannot be changed."""
    existing = ds.load_findings(args.course_code)
    d = args.model_dump(exclude={"course_code", "source_agent"})
    f = _commit(args.course_code, d, args.source_agent, existing)
    ds.save_findings(args.course_code, existing)
    return f


class RecordArgs(Args):
    path: str = Field(description="Spec path")
    check: Literal["structure", "bloom", "plo"] = Field(
        description="structure -> course-reviewer rules; bloom and plo -> curriculum-auditor rules")


@tool(permission="write")
def record_check_results(args: RecordArgs) -> dict:
    """Run one deterministic check (structure, bloom or plo) and append every resulting finding to the
    course's findings.json in a single step. Duplicates are skipped. Prefer this over copying drafts by hand."""
    spec = _spec(args.path)
    if not spec.course_code:
        raise ValueError("Spec has no course code; cannot file findings")
    agent = "course-reviewer" if args.check == "structure" else "curriculum-auditor"
    drafts = {"structure": lambda: rules.check_structure(spec),
              "bloom": lambda: rules.check_bloom(spec),
              "plo": lambda: rules.check_plo(spec, ds.plo_catalog())}[args.check]()
    existing = ds.load_findings(spec.course_code)
    stored = [_commit(spec.course_code, d, agent, existing) for d in drafts]
    ds.save_findings(spec.course_code, existing)
    new = [f for f in stored if not f.get("deduplicated")]
    return {"course_code": spec.course_code, "check": args.check, "added": len(new),
            "skipped_duplicates": len(stored) - len(new), "ids": [f["id"] for f in new],
            "open_totals": rules.compute_verdict(existing)["open_counts"]}


class ResolveArgs(Args):
    course_code: str
    finding_id: str
    resolution_note: str = Field(min_length=10, description="Why this finding is a false positive or has been fixed")
    resolved_by: str = Field(min_length=2, description="Name of the human reviewer")


@tool(permission="dangerous")
def resolve_finding(args: ResolveArgs) -> dict:
    """Mark a finding resolved with a note. Human reviewers only: this is the only way a blocker stops
    counting toward the verdict. Findings are never deleted."""
    findings = ds.load_findings(args.course_code)
    for f in findings:
        if f["id"] == args.finding_id:
            f.update(status="resolved", resolution_note=args.resolution_note,
                     resolved_by=args.resolved_by,
                     resolved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            ds.save_findings(args.course_code, findings)
            return {"resolved": args.finding_id}
    raise LookupError(f"No finding {args.finding_id} for {args.course_code}")


# ================================================================= write: reports
def _render_note(code: str, name: str, findings: list[dict], verdict: str) -> str:
    openf = [f for f in findings if f.get("status", "open") == "open"]
    lines = [f"# Review Note — {code}: {name}", "", f"**Verdict:** {verdict}", "", "## Findings", ""]
    for sev in SEVERITIES:
        for f in (x for x in openf if x["severity"] == sev):
            lines += [f"### [{sev.upper()}] {f['checklist_rule']} — {f['section']}",
                      f"> {f['quote']}", "", f["message"], "", f"**Fix:** {f['suggested_fix']}", ""]
    if not openf:
        lines += ["No open findings.", ""]
    refs = sorted({f["standard_ref"] for f in openf if f.get("standard_ref")})
    lines += ["## Standards cited"] + ([f"- {r}" for r in refs] or ["- (none)"])
    return "\n".join(lines) + "\n"


class NoteArgs(Args):
    course_code: str
    spec_path: str = Field(description="Spec path, used for the course name and instructor-facing title")


@tool(permission="write")
def write_review_note(args: NoteArgs) -> dict:
    """Write reports/<code>/REVIEW_NOTE.md. The verdict is computed from findings.json by the fixed policy
    table; you cannot supply one. Also appends to audit-log.jsonl and queues amendments for non-APPROVE."""
    spec = _spec(args.spec_path)
    code, name = args.course_code, spec.course_name or "(unnamed)"
    findings = ds.load_findings(code)
    if not findings and not ds.findings_path(code).is_file():
        raise FileNotFoundError(f"No findings.json for {code}: run the review stages first")
    v = rules.compute_verdict(findings)
    note = ds.reports_dir() / code / "REVIEW_NOTE.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(_render_note(code, name, findings, v["verdict"]), encoding="utf-8")

    with open(ds.reports_dir() / "audit-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "session_id": "harness", "course_code": code,
                            "verdict": v["verdict"], "finding_counts": v["open_counts"]}) + "\n")

    queued = 0
    if v["verdict"] != "APPROVE":
        qpath = ds.reports_dir() / "amendments-queue.csv"
        seen = set()
        if qpath.is_file():
            with open(qpath, newline="", encoding="utf-8") as fh:
                seen = {(r["course_code"], r["finding_id"]) for r in csv.DictReader(fh)}
        rows = [{"course_code": code, "course_name": name, "verdict": v["verdict"],
                 "finding_id": f["id"], "severity": f["severity"], "section": f["section"],
                 "summary": f["message"], "suggested_fix": f["suggested_fix"],
                 "owner": "unassigned", "due_date": ""}
                for f in findings if f.get("status", "open") == "open"
                and (code, f["id"]) not in seen]
        ds.append_csv(qpath, AMENDMENT_COLS, rows)
        queued = len(rows)
    return {"course_code": code, "verdict": v["verdict"], "open_counts": v["open_counts"],
            "note": _rel(note), "amendments_queued": queued}


class BatchArgs(Args):
    course_codes: list[str]


@tool(permission="write")
def write_batch_summary(args: BatchArgs) -> dict:
    """Write reports/COURSE_SPEC_REVIEW.md, one row per course, from the findings on disk.
    Verdicts come from the fixed policy table."""
    rows = []
    for code in args.course_codes:
        v = rules.compute_verdict(ds.load_findings(code))
        note = ds.reports_dir() / code / "REVIEW_NOTE.md"
        m = re.search(rf"# Review Note — {re.escape(code)}: (.*)", note.read_text(encoding="utf-8")) \
            if note.is_file() else None
        c = v["open_counts"]
        rows.append(f"| {code} | {m[1].strip() if m else '(no note)'} | {v['verdict']} | "
                    f"{c['blocker']} | {c['major']} | {c['minor']} |")
    text = "\n".join([f"# Course Spec Review — {date.today().isoformat()}", "",
                      "| Course Code | Course Name | Verdict | Blockers | Majors | Minors |",
                      "|---|---|---|---|---|---|", *rows, "",
                      "See `reports/<course_code>/REVIEW_NOTE.md` for per-course detail.",
                      "See `reports/PROGRAM_PLO_COVERAGE.md` for the batch PLO coverage rollup (batch mode only).",
                      ""])
    ds.reports_dir().mkdir(parents=True, exist_ok=True)
    (ds.reports_dir() / "COURSE_SPEC_REVIEW.md").write_text(text, encoding="utf-8")
    return {"written": _rel(ds.reports_dir() / "COURSE_SPEC_REVIEW.md"), "courses": len(rows)}


@tool(permission="write")
def write_plo_coverage_report(args: CoverageArgs) -> dict:
    """Write reports/PROGRAM_PLO_COVERAGE.md for a batch: covered PLOs, unverified-only coverage and gaps."""
    cov = rules.plo_coverage([_spec(p) for p in args.paths], ds.plo_catalog())
    cat = ds.plo_catalog()
    lines = ["# Program PLO Coverage", "", "| PLO | Status | Courses |", "|---|---|---|"]
    for p in cat:
        if p in cov["covered"]:
            lines.append(f"| {p} | covered | {', '.join(cov['covered'][p])} |")
        elif p in cov["unverified_only"]:
            lines.append(f"| {p} | coverage claimed but unverified | {', '.join(cov['unverified_only'][p])} |")
        else:
            lines.append(f"| {p} | **GAP** | — |")
    lines += ["", "Gaps matter for the TABEE self-study mapping matrix (references/tabee-standard.md).", ""]
    (ds.reports_dir() / "PROGRAM_PLO_COVERAGE.md").write_text("\n".join(lines), encoding="utf-8")
    return {"written": _rel(ds.reports_dir() / "PROGRAM_PLO_COVERAGE.md"), "gaps": cov["gaps"]}
