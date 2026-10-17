"""Orchestration: course-reviewer -> curriculum-auditor -> verdict-writer.

Mirrors commands/review-spec.md. Each plugin agent becomes a Stage with a prompt, a
tool allow-list and a permission set; the plugin's skills become tools (see qa_tools.py)
and its hooks become checks inside those tools.

Two modes share the same tools, executor and log:
  run_agents(...)         the model chooses tool calls (the harness/agent version)
  run_deterministic(...)  the pipeline calls the tools itself (no model; reference run)
"""
from __future__ import annotations

from . import qa_tools  # noqa: F401  (registers the tools)
from . import data_store as ds
from .agent_loop import AgentResult, Stage, run_stage
from .executor import execute
from .harness import Harness
from .logger import new_run_id
from .spec_parser import parse_spec

REVIEWER_CHECKS, AUDITOR_CHECKS = {"structure"}, {"bloom", "plo"}


def _check_guard(allowed_checks: set[str]):
    def guard(name: str, args: dict) -> str | None:
        if name == "record_check_results" and args.get("check") not in allowed_checks:
            return f"This stage may only record checks {sorted(allowed_checks)}"
        return None
    return guard


STAGES = {
    "course-reviewer": Stage(
        "course-reviewer", "course_reviewer",
        ["parse_course_spec", "check_weights", "run_structure_check", "record_check_results",
         "add_finding", "get_findings"],
        allowed=frozenset({"read", "write"}), inject={"source_agent": "course-reviewer"},
        guard=_check_guard(REVIEWER_CHECKS)),
    "curriculum-auditor": Stage(
        "curriculum-auditor", "curriculum_auditor",
        ["parse_course_spec", "bloom_review", "lookup_bloom_verb", "run_bloom_check",
         "get_plo_catalog", "validate_plo_ids", "run_plo_check", "record_check_results",
         "add_finding", "get_findings"],
        allowed=frozenset({"read", "write"}), inject={"source_agent": "curriculum-auditor"},
        guard=_check_guard(AUDITOR_CHECKS)),
    "verdict-writer": Stage(
        "verdict-writer", "verdict_writer",
        ["get_findings", "get_verdict", "write_review_note"],
        allowed=frozenset({"read", "write"})),   # no 'dangerous': cannot resolve findings
}


def _code_of(path: str) -> str:
    spec = parse_spec(ds.resolve_spec(path).read_text(encoding="utf-8"))
    if not spec.course_code:
        raise ValueError(f"{path}: no course code found")
    return spec.course_code


def run_agents(h: Harness, path: str, *, fresh: bool = True) -> dict:
    """Run the three model-driven stages on one spec. Returns a summary dict."""
    code = _code_of(path)
    if fresh and ds.findings_path(code).exists():
        ds.findings_path(code).unlink()
    run_id = new_run_id()
    results: list[AgentResult] = []
    cfg = h.config_agents

    def go(name: str, task: str) -> AgentResult:
        a = cfg.get(name, {})
        r = run_stage(h, STAGES[name], task, profile=a.get("profile", "reasoning"),
                      max_steps=a.get("max_steps", 8), run_id=run_id)
        results.append(r)
        return r

    go("course-reviewer", f"Review the course specification at {path}. Course code: {code}.")
    go("curriculum-auditor", f"Audit the course specification at {path}. Course code: {code}.")
    go("verdict-writer", f"Write the review note for course {code} (spec: {path}).")
    verdict = _verdict(code)
    return {"course_code": code, "run_id": run_id, "verdict": verdict,
            "stages": [{"stage": r.stage, "steps": r.steps, "stopped": r.stopped,
                        "tool_errors": len(r.errors), "wall_s": round(r.wall_s, 2)}
                       for r in results]}


def run_deterministic(h: Harness, path: str, *, fresh: bool = True) -> dict:
    """Same tools, no model. The reference the agent run is scored against."""
    code = _code_of(path)
    if fresh and ds.findings_path(code).exists():
        ds.findings_path(code).unlink()
    run_id = new_run_id()

    def call(name: str, args: dict) -> dict:
        out = execute({"function": {"name": name, "arguments": args}},
                      allowed={"read", "write"}, logger=h.log, run_id=run_id)
        if not out["ok"]:
            raise RuntimeError(f"{name}: {out['error']}")
        return out["result"]

    for check in ("structure", "bloom", "plo"):
        call("record_check_results", {"path": path, "check": check})
    call("write_review_note", {"course_code": code, "spec_path": path})
    return {"course_code": code, "run_id": run_id, "verdict": _verdict(code), "stages": []}


def _verdict(code: str) -> dict:
    from .qa_rules import compute_verdict
    return compute_verdict(ds.load_findings(code))


def finish_batch(h: Harness, paths: list[str], codes: list[str]) -> None:
    """After the last course: batch summary and PLO coverage rollup."""
    run_id = new_run_id()
    for name, args in (("write_batch_summary", {"course_codes": codes}),
                       ("write_plo_coverage_report", {"paths": paths})):
        execute({"function": {"name": name, "arguments": args}}, allowed={"read", "write"},
                logger=h.log, run_id=run_id)
