"""Orchestration: course-reviewer -> curriculum-auditor -> verdict-writer (commands/review-spec.md).

Each plugin agent is a Stage: a prompt, a tool allow-list and a permission set. Its skills
are tools (qa_tools.py) and its hooks are checks inside those tools.

  run_agents(...)         the model chooses the tool calls (M8 loop per stage, fixed order)
  run_deterministic(...)  the pipeline calls the same tools itself (no model): the reference run
  state_machine.run_sm    the same stages inside INTAKE -> ... -> DONE, with a router (M9-M11)

All clear reports/<code>/ first (README: "clear reports/<course_code>/ before reviewing
again"), and skip curriculum-auditor when the form gate F.1 failed.
"""
from __future__ import annotations

from pathlib import Path

from . import qa_tools  # noqa: F401  (registers the tools)
from . import data_store as ds
from .agent_loop import AgentResult, Stage, run_stage
from .completion import CHECKS
from .executor import execute
from .harness import Harness
from .logger import new_run_id
from .qa_rules import compute_verdict
from .spec_parser import parse_spec

RW = frozenset({"read", "write"})


def _check_guard(allowed: set[str]):
    def guard(name: str, args: dict) -> str | None:
        if name == "record_check_results" and args.get("check") not in allowed:
            return f"This stage may only record checks {sorted(allowed)}"
        return None
    return guard


STAGES = {
    "course-reviewer": Stage(
        "course-reviewer", "course_reviewer",
        ["parse_course_spec", "check_form_gate", "check_weights", "read_course_spec", "run_reviewer_checks",
         "record_check_results", "get_checklist_rule", "add_finding", "get_findings"],
        allowed=RW, inject={"source_agent": "course-reviewer"}, guard=_check_guard({"structure"})),
    "curriculum-auditor": Stage(
        "curriculum-auditor", "curriculum_auditor",
        ["parse_course_spec", "derive_clo_levels", "lookup_bloom_verb", "set_clo_level", "run_bloom_checks",
         "run_plo_checks", "get_plo_catalog", "record_check_results", "get_checklist_rule", "add_finding",
         "get_findings"],
        allowed=RW, inject={"source_agent": "curriculum-auditor"}, guard=_check_guard({"bloom", "plo"})),
    "verdict-writer": Stage(
        "verdict-writer", "verdict_writer",
        ["get_findings", "get_verdict", "write_review_note"],
        allowed=RW),          # no 'dangerous': cannot resolve findings
}

TASKS = {
    "course-reviewer": "Review the course specification at {path}. Course code: {code}.",
    "curriculum-auditor": "Audit the course specification at {path}. Course code: {code}.",
    "verdict-writer": "Write the review note for course {code} (spec: {path}).",
}


def _code_of(path: str) -> str:
    p = ds.resolve_spec(path)
    return parse_spec(p.read_text(encoding="utf-8")).course_code or p.stem


def _f1_failed(code: str) -> bool:
    return any(f["checklist_rule"] == "F.1" and f.get("status", "open") == "open"
               for f in ds.load_findings(code))


def _prepare(path: str, fresh: bool) -> str:
    code = _code_of(path)
    if fresh:
        ds.clear_course(code)
    elif ds.findings_path(code).exists():
        raise FileExistsError(f"reports/{code}/findings.json is from an earlier run: clear it or use fresh=True")
    return code


def run_agents(h: Harness, path: str, *, fresh: bool = True, profile: str | None = None) -> dict:
    """Run the three model-driven stages on one spec. `profile` forces one model for every
    stage (the single-model baseline); otherwise each stage uses its `agents:` profile."""
    code = _prepare(path, fresh)
    run_id = new_run_id()
    results: list[AgentResult] = []

    def go(name: str) -> None:
        a = h.config_agents.get(name, {})
        results.append(run_stage(h, STAGES[name], TASKS[name].format(path=path, code=code),
                                 profile=profile or a.get("profile", "reasoning"),
                                 max_steps=a.get("max_steps", 8), max_errors=a.get("max_errors", 4),
                                 check=lambda: CHECKS[name](path), run_id=run_id))

    go("course-reviewer")
    if not ds.findings_path(code).exists():
        # the model never recorded anything: record the structure check so later stages have a file
        execute({"function": {"name": "record_check_results", "arguments": {"path": path, "check": "structure"}}},
                allowed=set(RW), logger=h.log, run_id=run_id)
    if not _f1_failed(code):
        go("curriculum-auditor")
    go("verdict-writer")
    return _summary(code, run_id, results)


def run_deterministic(h: Harness, path: str, *, fresh: bool = True) -> dict:
    """Same tools, same order, no model."""
    code = _prepare(path, fresh)
    run_id = new_run_id()

    def call(name: str, args: dict) -> dict:
        out = execute({"function": {"name": name, "arguments": args}}, allowed=set(RW),
                      logger=h.log, run_id=run_id)
        if not out["ok"]:
            raise RuntimeError(f"{name}: {out['error']}")
        return out["result"]

    call("record_check_results", {"path": path, "check": "structure"})
    if not _f1_failed(code):
        call("record_check_results", {"path": path, "check": "bloom"})
        call("record_check_results", {"path": path, "check": "plo"})
    call("write_review_note", {"course_code": code, "spec_path": path})
    return _summary(code, run_id, [])


def stage_row(r: AgentResult) -> dict:
    return {"stage": r.stage, "profile": r.profile, "steps": r.steps, "stopped": r.stopped,
            "verified": r.verified, "tool_calls": len(r.calls), "tool_errors": len(r.errors),
            "wall_s": round(r.wall_s, 2),
            "load_s": round(sum(t["load_s"] for t in r.trace), 2)}


def _summary(code: str, run_id: str, results: list[AgentResult]) -> dict:
    return {"course_code": code, "run_id": run_id, "verdict": compute_verdict(ds.load_findings(code)),
            "f1_failed": _f1_failed(code), "stages": [stage_row(r) for r in results]}


def finish_batch(h: Harness, paths: list[str], codes: list[str]) -> None:
    """After the last course: PLO coverage rollup, then the batch summary."""
    run_id = new_run_id()
    for name, args in (("write_plo_coverage_report", {"paths": paths}),
                       ("write_batch_summary", {"course_codes": codes})):
        execute({"function": {"name": name, "arguments": args}}, allowed=set(RW), logger=h.log, run_id=run_id)


def batch_paths(directory: str | None = None) -> list[str]:
    """--all: every .md in courses/ (or in the given directory), never evaluation/ or reports/."""
    if directory is None:
        return ds.list_specs()
    d = (ds.root() / directory).resolve()
    return sorted(ds.rel(p) for p in d.glob("*.md") if p.is_file()
                  and Path(ds.rel(p)).parts[0] not in ds.NOT_REVIEWABLE)
