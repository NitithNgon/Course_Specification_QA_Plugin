"""M6 tools for the Course Specification QA pipeline. Importing registers them.

Design rule: anything with one right answer is a tool (parsing the form, the weight sum,
verb lookup, PLO validity, the 41 checklist rules, severity, the verdict, report rendering).
The model decides only what the rules cannot: which tool to call next, the level of a CLO
verb the dictionary does not cover (set_clo_level), and 2.7 advisory findings (add_finding).

The plugin's guarantees, enforced here rather than by Claude Code hooks:
  validate_findings.py         every findings.json write runs the plugin's own validator
                               (rule exists, severity and owner from checklist.md, required
                               fields, append-only); the model never supplies a severity
  block_approve_with_blocker   write_review_note takes no verdict; it computes it from findings
  log_verdict.py               write_review_note appends the audit line (with rulebook sha256)
  "only a human resolves"      resolve_finding needs 'dangerous', which no stage is granted

Permissions (checked by executor.execute(allowed=...)):
  read  inspect specs, the rulebook and findings; run checks without saving
  write record findings, record a CLO-level judgment, write reports
  dangerous  resolve_finding
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import data_store as ds
from . import qa_rules as rules
from .spec_parser import Spec, parse_spec
from .tools import tool

MAX_LINES = 200
SEVERITIES = ("blocker", "major", "minor")
AMENDMENT_COLS = ["course_code", "course_name", "verdict", "finding_id", "severity", "section",
                  "summary", "suggested_fix", "owner", "due_date"]
Level = Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
SCOPE_OWNER = {"structure": "course-reviewer", "bloom": "curriculum-auditor", "plo": "curriculum-auditor"}


class Args(BaseModel):
    """Unknown argument names are rejected, so a model cannot slip in e.g. verdict="APPROVE"."""
    model_config = ConfigDict(extra="forbid")


def _load(path: str) -> tuple[Spec, Path]:
    p = ds.resolve_spec(path)
    return parse_spec(p.read_text(encoding="utf-8"), ds.rel(p)), p


def _code(spec: Spec, p: Path) -> str:
    return spec.course_code or p.stem      # agents/course-reviewer.md: else the file name


def _overrides(code: str) -> dict:
    return ds.load_json(code, "clo_levels.json", {})


def _drafts(spec: Spec, p: Path, check: str) -> list[dict]:
    code = _code(spec, p)
    return {"structure": lambda: rules.check_structure(spec, p.stem),
            "bloom": lambda: rules.check_bloom(spec, _overrides(code)),
            "plo": lambda: rules.check_plo(spec)}[check]()


# ================================================================ read: documents
class NoArgs(Args):
    pass


class PathArgs(Args):
    path: str = Field(description="Spec path as returned by list_course_specs, e.g. courses/CPE201.md")


@tool(permission="read")
def list_course_specs(args: NoArgs) -> dict:
    """List the course specification files in courses/ (paths relative to the plugin root)."""
    return {"specs": ds.list_specs()}


class ReadArgs(Args):
    path: str = Field(description="Spec path")
    start_line: int = Field(default=1, ge=1)
    max_lines: int = Field(default=MAX_LINES, ge=1, le=MAX_LINES)


@tool(permission="read")
def read_course_spec(args: ReadArgs) -> dict:
    """Return lines of a spec with their line numbers. Use to quote a row exactly or to read the assessment note."""
    lines = ds.resolve_spec(args.path).read_text(encoding="utf-8").splitlines()
    end = min(len(lines), args.start_line - 1 + args.max_lines)
    return {"path": args.path, "total_lines": len(lines),
            "lines": [f"{i}: {lines[i - 1]}" for i in range(args.start_line, end + 1)]}


@tool(permission="read")
def parse_course_spec(args: PathArgs) -> dict:
    """Extract the form verbatim with line numbers: course code and title, form-gate parts, related PLOs,
    CLO table, assessment table (with method type), grade thresholds and the assessment note. Call this first."""
    spec, p = _load(args.path)
    return {
        "course_code": _code(spec, p), "course_title": spec.course_title,
        "on_official_form": not rules.f1_failed(spec), "form_gate_missing": rules.form_gate(spec),
        "related_plos": [f"{l.no}: {l.text}" for l in spec.related_plo_lines()],
        "clos": [{"id": c.id, "text": c.text, "plos": c.plos, "plo_cell": c.plo_cell, "line": c.line.no}
                 for c in spec.clos],
        "methods": [{"method": m.name, "level": m.level, "clos": m.clos, "weight": m.weight, "line": m.line.no,
                     "type": rules.method_type(m)[0], "exempt_attendance": rules.is_exempt(m)}
                    for m in spec.methods],
        "grades": [{"grade": g, "threshold": v, "line": ln.no} for g, v, ln in spec.grades()],
        "assessment_note": [f"{l.no}: {l.text}" for l in spec.assessment_note()],
        "sections": [s.title for s in spec.sections.values()],
    }


@tool(permission="read")
def check_form_gate(args: PathArgs) -> dict:
    """Rule F.1: is the document on the official form? Lists each missing part. If it fails, no other rule is checked."""
    spec, _ = _load(args.path)
    missing = rules.form_gate(spec)
    return {"on_official_form": not missing, "missing": missing}


@tool(permission="read")
def check_weights(args: PathArgs) -> dict:
    """Exact assessment-weight sum (bonus rows excluded), its difference from 100, and every sub-part split
    stated in the assessment note (rule 4.10). Use instead of adding numbers yourself."""
    spec, _ = _load(args.path)
    return rules.weight_report(spec)


# ============================================================== read: rulebook
class RuleArgs(Args):
    rule_id: str = Field(description="Checklist rule ID, e.g. '4.7' or 'F.1'")


@tool(permission="read")
def get_checklist_rule(args: RuleArgs) -> dict:
    """Return one rule from references/checklist.md: what it checks, its severity and its owning agent."""
    r = ds.checklist().get(args.rule_id)
    if r is None:
        raise LookupError(f"No rule {args.rule_id!r}. Rules: {', '.join(ds.checklist())}")
    return {"rule": args.rule_id, **r}


class VerbArgs(Args):
    verb: str = Field(description="One English verb in base form, e.g. 'critique'")


@tool(permission="read")
def lookup_bloom_verb(args: VerbArgs) -> dict:
    """Look up a verb in bloom-taxonomy.md (dictionary or convention) or the harness synonym table.
    Returns its level and how it was classified, or null."""
    hit = rules.lookup(args.verb.strip().lower())
    return {"verb": args.verb, "level": hit[0] if hit else None, "how": hit[1] if hit else None,
            "note": None if hit else "not classified: decide by a clear synonym and record it with set_clo_level"}


@tool(permission="read")
def get_plo_catalog(args: NoArgs) -> dict:
    """Return the program's PLO catalog (PLO ID -> statement and WA attribute). Valid IDs are exactly these."""
    return ds.plo_catalog()


# ========================================================= read: run the checks
class CheckArgs(Args):
    path: str = Field(description="Spec path")


@tool(permission="read")
def run_reviewer_checks(args: CheckArgs) -> dict:
    """Run every course-reviewer rule (F.1, 1.x, 2.1, 2.3, 2.4, 3.x, 4.1-4.6, 4.10, 5.x, 6.x, 7.x) with the
    checklist's precedence list. Returns draft findings; saves nothing."""
    spec, p = _load(args.path)
    d = _drafts(spec, p, "structure")
    return {"count": len(d), "findings": d}


@tool(permission="read")
def derive_clo_levels(args: CheckArgs) -> dict:
    """Derive each CLO's Bloom level from its student verbs (bloom-taxonomy.md, 'Deriving a CLO's level').
    Shows each verb and how it was classified. A CLO with no classified verb is listed under needs_judgment:
    decide whether it really is a teaching aim (rule 2.2) or has a verb you can classify by synonym."""
    spec, p = _load(args.path)
    lv = rules.clo_levels(spec, _overrides(_code(spec, p)))
    return {"clos": [{"clo": c.id, "text": c.text, "level": lv[c.id]["level"], "verbs": lv[c.id]["verbs"],
                      "recorded_judgment": lv[c.id].get("override")} for c in spec.clos],
            "needs_judgment": [c.id for c in spec.clos if not lv[c.id]["classifiable"]
                               and not lv[c.id].get("override")]}


@tool(permission="read")
def run_bloom_checks(args: CheckArgs) -> dict:
    """Run rules 2.2, 4.7, 4.8 and 4.9 (CLO verbs vs each method's stated level and method type), applying any
    level recorded with set_clo_level. Returns draft findings with Bloom citations; saves nothing."""
    spec, p = _load(args.path)
    d = _drafts(spec, p, "bloom")
    return {"count": len(d), "findings": d}


@tool(permission="read")
def run_plo_checks(args: CheckArgs) -> dict:
    """Run rules 2.5 (PLO ID not in the catalog) and 2.6 (CLO PLOs differ from the related-PLO section).
    Returns draft findings; saves nothing."""
    spec, p = _load(args.path)
    d = _drafts(spec, p, "plo")
    return {"count": len(d), "findings": d}


class CoverageArgs(Args):
    paths: list[str] = Field(description="Spec paths in this batch")


def _coverage(paths: list[str]) -> list[dict]:
    specs = [_load(p)[0] for p in paths]
    blocked = {s.course_code: bool(rules.compute_verdict(ds.load_findings(s.course_code))["open_blocker_ids"])
               for s in specs if s.course_code}
    return rules.plo_coverage(specs, blocked)


@tool(permission="read")
def plo_coverage_rollup(args: CoverageArgs) -> dict:
    """Program PLO coverage for a batch: per PLO, courses with and without an open blocker, and the status
    (covered / claimed, not yet approved / gap). Run after the courses' findings are recorded."""
    return {"plos": _coverage(args.paths)}


# ============================================================ read: findings state
class CourseArgs(Args):
    course_code: str = Field(description="Course code, e.g. CPE201")


@tool(permission="read")
def get_findings(args: CourseArgs) -> dict:
    """Return every finding recorded so far for a course (reports/<code>/findings.json)."""
    f = ds.load_findings(args.course_code)
    return {"course_code": args.course_code, "count": len(f), "findings": f}


@tool(permission="read")
def get_verdict(args: CourseArgs) -> dict:
    """Apply the fixed verdict policy to a course's findings: RETURN if any open blocker, REVISE if any open
    major, else APPROVE. A lookup, not a judgment."""
    return {"course_code": args.course_code, **rules.compute_verdict(ds.load_findings(args.course_code))}


# ================================================================ write: findings
def _commit(code: str, drafts: list[dict]) -> tuple[list[dict], list[dict]]:
    """Append drafts (skipping duplicates) and save through the plugin's validator."""
    existing = ds.load_findings(code)
    added, dupes = [], []
    for d in drafts:
        same = next((f for f in existing if f["checklist_rule"] == d["checklist_rule"]
                     and f["section"] == d["section"] and f["quote"] == d["quote"]), None)
        if same:
            dupes.append(same)
            continue
        f = {"id": f"F{len(existing) + 1:03d}", **{k: v for k, v in d.items()}, "status": "open"}
        existing.append(f)
        added.append(f)
    ds.save_findings(code, existing)
    return added, dupes


class FindingArgs(Args):
    course_code: str
    source_agent: Literal["course-reviewer", "curriculum-auditor"] = Field(
        description="Set by the pipeline stage; must be the rule's owner in checklist.md")
    checklist_rule: str = Field(description="Rule ID from checklist.md, e.g. '2.7'")
    section: str = Field(min_length=3, description="Pointer to the row, e.g. 'Course learning outcomes, row \"CLO1\" (line 43)'")
    quote: str = Field(min_length=1, description="The row or text exactly as printed, '-' as printed, or '(absent)'")
    message: str = Field(min_length=5)
    suggested_fix: str = Field(min_length=5, description="One sentence an instructor can act on")
    standard_ref: str | None = Field(default=None, description="Required for curriculum-auditor: the standard and rule cited")


@tool(permission="write")
def add_finding(args: FindingArgs) -> dict:
    """Record one judgment-based finding, e.g. a 2.7 advisory (an obvious CLO-to-PLO misfit, saying why).
    Severity is taken from checklist.md; the rule must be owned by your stage. Use record_check_results
    for everything the rule checks already find."""
    rule = ds.checklist().get(args.checklist_rule)
    if rule is None:
        raise ValueError(f"checklist_rule {args.checklist_rule!r} is not a rule in checklist.md")
    if rule["owner"] != args.source_agent:
        raise ValueError(f"Rule {args.checklist_rule} is owned by {rule['owner']}, not {args.source_agent}")
    if args.source_agent == "curriculum-auditor" and not args.standard_ref:
        raise ValueError("curriculum-auditor findings must cite a standard_ref")
    d = {"checklist_rule": args.checklist_rule, "severity": rule["severity"], "source_agent": args.source_agent,
         "section": args.section, "quote": args.quote, "standard_ref": args.standard_ref,
         "message": args.message, "suggested_fix": args.suggested_fix}
    added, dupes = _commit(args.course_code, [d])
    return added[0] if added else {**dupes[0], "deduplicated": True}


class RecordArgs(Args):
    path: str = Field(description="Spec path")
    check: Literal["structure", "bloom", "plo"] = Field(
        description="structure = course-reviewer rules; bloom and plo = curriculum-auditor rules")


@tool(permission="write")
def record_check_results(args: RecordArgs) -> dict:
    """Run one rule check (structure, bloom or plo) and append every resulting finding to the course's
    findings.json in one step, through the plugin's validator. Creates findings.json even when there are none."""
    spec, p = _load(args.path)
    code = _code(spec, p)
    owner = SCOPE_OWNER[args.check]
    drafts = _drafts(spec, p, args.check)
    mine = [d for d in drafts if d["source_agent"] == owner]
    added, dupes = _commit(code, mine)
    return {"course_code": code, "check": args.check, "added": len(added), "ids": [f["id"] for f in added],
            "skipped_duplicates": len(dupes),
            "skipped_other_owner": [d["checklist_rule"] for d in drafts if d["source_agent"] != owner],
            "form_gate_failed": rules.f1_failed(spec),
            "open_totals": rules.compute_verdict(ds.load_findings(code))["open_counts"]}


class CloLevelArgs(Args):
    course_code: str
    clo: str = Field(description="CLO ID, e.g. CLO2")
    level: Level | None = Field(description="The CLO's level, or null if it has no student verb (teaching aim)")
    verbs: list[str] = Field(default_factory=list, description="The student verbs you classified")
    reason: str = Field(min_length=10, description="e.g. \"'build' classified as Create by analogy to 'construct'\"")


@tool(permission="write")
def set_clo_level(args: CloLevelArgs) -> dict:
    """Record your judgment of a CLO's Bloom level when its verb is not in the dictionary (deriving rule 3),
    or confirm it is a teaching aim (level null). Saved in the reviewer notes (clo_levels.json) and used by
    run_bloom_checks and record_check_results(check='bloom'). A synonym match is never a finding."""
    o = _overrides(args.course_code)
    o[args.clo.upper()] = {"level": args.level, "verbs": args.verbs, "reason": args.reason}
    ds.save_json(args.course_code, "clo_levels.json", o)
    return {"recorded": args.clo.upper(), **o[args.clo.upper()]}


class ResolveArgs(Args):
    course_code: str
    finding_id: str
    resolution_note: str = Field(min_length=10, description="Why the finding is a false positive or has been fixed")
    resolved_by: str = Field(min_length=2, description="Name of the human reviewer")


@tool(permission="dangerous")
def resolve_finding(args: ResolveArgs) -> dict:
    """Mark a finding resolved with a note. Human reviewers only: the only way a blocker stops counting.
    Findings are never deleted or rewritten."""
    findings = ds.load_findings(args.course_code)
    for f in findings:
        if f["id"] == args.finding_id:
            f.update(status="resolved", resolution_note=f"{args.resolution_note} (by {args.resolved_by})")
            ds.save_findings(args.course_code, findings)
            return {"resolved": args.finding_id}
    raise LookupError(f"No finding {args.finding_id} for {args.course_code}")


# ================================================================== write: reports
def _owner(spec: Spec) -> str:
    coord = spec.info().get("course coordinator")
    if coord and coord[0].strip() not in ("", "-"):
        return coord[0].strip()
    instr = spec.instructors()
    return instr[0][0] if instr else "unassigned"


def _render_note(code: str, name: str, findings: list[dict], verdict: str) -> str:
    openf = [f for f in findings if str(f.get("status", "open")).lower() != "resolved"]
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
    spec_path: str = Field(description="Spec path, for the course name and the amendments owner")


@tool(permission="write")
def write_review_note(args: NoteArgs) -> dict:
    """Write reports/<code>/REVIEW_NOTE.md. The verdict is computed from findings.json by the fixed policy table;
    you cannot supply one. Also appends to reports/audit-log.jsonl and, for a non-APPROVE verdict, one row per
    open finding to reports/amendments-queue.csv."""
    spec, _ = _load(args.spec_path)
    code, name = args.course_code, spec.course_title or "(untitled)"
    if not ds.findings_path(code).is_file():
        raise FileNotFoundError(f"No findings.json for {code}: run course-reviewer first")
    findings = ds.load_findings(code)
    v = rules.compute_verdict(findings)
    note = ds.course_dir(code) / "REVIEW_NOTE.md"
    note.write_text(_render_note(code, name, findings, v["verdict"]), encoding="utf-8")

    log = ds.reports_dir() / "audit-log.jsonl"
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "session_id": "harness",
                             "course_code": code, "verdict": v["verdict"], "finding_counts": v["open_counts"],
                             "resolved_count": v["resolved_count"],
                             "rulebook_sha256": ds.rulebook_sha256()}) + "\n")

    queued = 0
    if v["verdict"] != "APPROVE":
        qpath = ds.reports_dir() / "amendments-queue.csv"
        seen = set()
        if qpath.is_file():
            with open(qpath, newline="", encoding="utf-8") as fh:
                seen = {(r["course_code"], r["finding_id"]) for r in csv.DictReader(fh)}
        owner = _owner(spec)
        rows = [{"course_code": code, "course_name": name, "verdict": v["verdict"], "finding_id": f["id"],
                 "severity": f["severity"], "section": f["section"], "summary": f["message"],
                 "suggested_fix": f["suggested_fix"], "owner": owner, "due_date": ""}
                for f in findings if str(f.get("status", "open")).lower() != "resolved"
                and (code, f["id"]) not in seen]
        ds.append_csv(qpath, AMENDMENT_COLS, rows)
        queued = len(rows)
    return {"course_code": code, "verdict": v["verdict"], "open_counts": v["open_counts"],
            "note": ds.rel(note), "amendments_queued": queued}


class BatchArgs(Args):
    course_codes: list[str]


@tool(permission="write")
def write_batch_summary(args: BatchArgs) -> dict:
    """Write reports/COURSE_SPEC_REVIEW.md, one row per course, from the findings on disk.
    Verdicts come from the fixed policy table; a course the state machine escalated shows ESCALATED."""
    rows = []
    for code in args.course_codes:
        v = rules.compute_verdict(ds.load_findings(code))
        note = ds.course_dir(code) / "REVIEW_NOTE.md"
        m = re.search(rf"# Review Note — {re.escape(code)}: (.*)", note.read_text(encoding="utf-8")) \
            if note.is_file() else None
        c = v["open_counts"]
        verdict = "ESCALATED" if (ds.course_dir(code) / "ESCALATION.md").is_file() else v["verdict"]
        rows.append(f"| {code} | {m[1].strip() if m else '(no note)'} | {verdict} | "
                    f"{c['blocker']} | {c['major']} | {c['minor']} |")
    text = "\n".join([f"# Course Spec Review — {date.today().isoformat()}", "",
                      "| Course Code | Course Name | Verdict | Blockers | Majors | Minors |",
                      "|---|---|---|---|---|---|", *rows, "",
                      "See `reports/<course_code>/REVIEW_NOTE.md` for per-course detail.",
                      "See `reports/PROGRAM_PLO_COVERAGE.md` for the batch PLO coverage rollup (batch mode only).",
                      ""])
    ds.reports_dir().mkdir(parents=True, exist_ok=True)
    out = ds.reports_dir() / "COURSE_SPEC_REVIEW.md"
    out.write_text(text, encoding="utf-8")
    return {"written": ds.rel(out), "courses": len(rows)}


@tool(permission="write")
def write_plo_coverage_report(args: CoverageArgs) -> dict:
    """Write reports/PROGRAM_PLO_COVERAGE.md for a batch, in the plo-mapping-standard format, with the gaps
    listed under the table."""
    cov = _coverage(args.paths)
    lines = [f"# Program PLO Coverage — {date.today().isoformat()}", "",
             "| PLO | WA attribute | Courses with no open blocker | Courses with an open blocker | Status |",
             "|---|---|---|---|---|"]
    for r in cov:
        lines.append(f"| {r['plo']} | {r['wa']} | {', '.join(r['clean']) or '—'} | "
                     f"{', '.join(r['blocked']) or '—'} | {r['status']} |")
    gaps = [r["plo"] for r in cov if r["status"] == "gap"]
    lines += ["", "Gaps: " + (", ".join(gaps) if gaps else "none") + ". A PLO no course covers is a gap in the "
              "course-to-PLO mapping a TABEE self-study relies on (references/tabee-standard.md).", ""]
    ds.reports_dir().mkdir(parents=True, exist_ok=True)
    out = ds.reports_dir() / "PROGRAM_PLO_COVERAGE.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return {"written": ds.rel(out), "gaps": gaps}
