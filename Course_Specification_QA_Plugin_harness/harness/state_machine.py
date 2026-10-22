"""M9 - State machine: one course review as explicit states and allowed transitions.

    INTAKE -> CLASSIFY -> PLAN -> ACT -> VERIFY -> DONE
                 |         |      |      |   |
                 |         |      |      |   +-- re-plan (max 2) --> PLAN
                 +---------+------+------+-----> ESCALATE (human / safe failure)

Loop inside a state, state machine across the workflow: ACT runs the M8 agent loop once per
plan step; the transitions between states are fixed in TRANSITIONS.

  state     tools the model gets      output               next if OK
  INTAKE    none (code reads spec)    facts                CLASSIFY
  CLASSIFY  none                      TaskClass (M10)      PLAN
  PLAN      none (plan templates)     plan steps           ACT
  ACT       per step, by kind         tool results         VERIFY
  VERIFY    none (read-only checks)   problems             DONE or PLAN

PLAN and VERIFY are code, not model calls: commands/review-spec.md fixes the stage order,
and every completion criterion has one right answer (completion.py). The model's choices
are the tool calls inside ACT, routed per step by router.py (M11).

The RunState is saved to SQLite (runs.sqlite next to logs/calls.jsonl) after every
transition and every ACT step, so resume(run_id) continues a crashed run from its last
saved state. Re-running a step is safe because record_check_results skips duplicates.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from . import data_store as ds
from .agent_loop import run_stage
from .classifier import classify, facts_of
from .completion import CHECKS
from .harness import Harness
from .logger import new_run_id
from .pipeline import STAGES, TASKS, _f1_failed, _prepare, stage_row
from .qa_rules import compute_verdict
from .router import route, stage_ctx


class S(str, Enum):
    INTAKE = "intake"
    CLASSIFY = "classify"
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    DONE = "done"
    ESCALATE = "escalate"


TRANSITIONS: dict[S, set[S]] = {
    S.INTAKE:   {S.CLASSIFY},
    S.CLASSIFY: {S.PLAN, S.ESCALATE},
    S.PLAN:     {S.ACT, S.ESCALATE},
    S.ACT:      {S.VERIFY, S.ESCALATE},
    S.VERIFY:   {S.DONE, S.PLAN, S.ESCALATE},
}
TERMINAL = {S.DONE, S.ESCALATE}

# PLAN templates in commands/review-spec.md order: (stage, kind). The kind is the route key.
PLANS = {
    "off_form":       [("course-reviewer", "gate"), ("verdict-writer", "write")],
    "standard":       [("course-reviewer", "review"), ("curriculum-auditor", "audit"),
                       ("verdict-writer", "write")],
    "needs_judgment": [("course-reviewer", "review"), ("curriculum-auditor", "judge"),
                       ("verdict-writer", "write")],
}

# Per-state allow-lists: offer only the tools this kind of step needs (too many tools -> wrong pick)
NARROW = {
    "gate": ["check_form_gate", "record_check_results", "get_findings"],
    "audit": [t for t in STAGES["curriculum-auditor"].tools
              if t not in ("set_clo_level", "lookup_bloom_verb")],
}


class IllegalTransition(RuntimeError):
    def __init__(self, src: S, dst: S):
        super().__init__(f"{src.name} -> {dst.name} is not an allowed transition")
        self.src, self.dst = src, dst


class Transition(BaseModel):
    src: S
    dst: S
    reason: str = ""
    at: str


class PlanStep(BaseModel):
    stage: str
    kind: str
    task: str
    done: bool = False


class RunState(BaseModel):
    run_id: str
    path: str
    course_code: str = ""
    state: S = S.INTAKE
    facts: dict = Field(default_factory=dict)
    task_type: str | None = None
    classified_by: str | None = None
    plan: list[PlanStep] = Field(default_factory=list)
    replans: int = 0
    failures: dict[str, int] = Field(default_factory=dict)   # failed attempts per stage: router input
    problems: list[dict] = Field(default_factory=list)       # last VERIFY: [{stage, problem}]
    stages: list[dict] = Field(default_factory=list)         # one row per ACT step attempt
    reason: str = ""                                         # why it escalated
    history: list[Transition] = Field(default_factory=list)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Checkpoints:
    """SQLite store: one row per run, holding the RunState as JSON."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, course_code TEXT, "
                        "state TEXT, updated_at TEXT, data TEXT NOT NULL)")

    def save(self, run: RunState) -> None:
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?)",
                        (run.run_id, run.course_code, run.state.value, _now(), run.model_dump_json()))

    def load(self, run_id: str) -> RunState:
        with closing(sqlite3.connect(self.path)) as con:
            row = con.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"No run {run_id!r} in {self.path}")
        return RunState.model_validate_json(row[0])

    def runs(self, limit: int = 20) -> list[tuple[str, str, str, str]]:
        """(run_id, course_code, state, updated_at), newest first."""
        with closing(sqlite3.connect(self.path)) as con:
            return con.execute("SELECT run_id, course_code, state, updated_at FROM runs "
                               "ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()


def store_for(h: Harness) -> Checkpoints:
    return Checkpoints(h.log.path.with_name("runs.sqlite"))


def advance(run: RunState, nxt: S, reason: str = "", *, store: Checkpoints | None = None,
            log=None) -> None:
    if nxt not in TRANSITIONS.get(run.state, set()):
        raise IllegalTransition(run.state, nxt)
    run.history.append(Transition(src=run.state, dst=nxt, reason=reason, at=_now()))
    if log is not None:
        log.write("transition", run_id=run.run_id, course_code=run.course_code,
                  src=run.state.value, dst=nxt.value, reason=reason)
    run.state = nxt
    if store is not None:
        store.save(run)                      # SQLite checkpoint


# ------------------------------------------------------------------ state handlers
# Each takes (h, run, store) and returns (next state, reason). drive() applies the move.
def _intake(h: Harness, run: RunState, store: Checkpoints) -> tuple[S, str]:
    run.facts = facts_of(run.path)
    run.course_code = run.facts["course_code"]
    f = run.facts
    return S.CLASSIFY, (f"{run.course_code}: on_official_form={f['on_official_form']}, "
                        f"{f['clos']} CLOs, {f['methods']} assessment rows")


def _classify(h: Harness, run: RunState, store: Checkpoints) -> tuple[S, str]:
    c, how = classify(h, run.facts, run_id=run.run_id)
    if c is None:
        return S.ESCALATE, "task type undecided by the rules, the small model and the main LLM"
    run.task_type, run.classified_by = c.task_type, how
    return S.PLAN, f"{c.task_type} by {how}: {c.reason}"


def _task(run: RunState, stage: str, note: str | None) -> str:
    t = TASKS[stage].format(path=run.path, code=run.course_code)
    return f"{t}\nAn earlier attempt did not finish: {note}" if note else t


def _plan(h: Harness, run: RunState, store: Checkpoints) -> tuple[S, str]:
    full = PLANS.get(run.task_type or "")
    if full is None:
        return S.ESCALATE, f"no plan for task type {run.task_type!r}"
    steps, notes, label = full, {}, ""
    if run.problems:                         # re-plan from the first stage that failed a check
        failed = {p["stage"] for p in run.problems}
        steps = full[next(i for i, (stage, _) in enumerate(full) if stage in failed):]
        notes = {p["stage"]: p["problem"] for p in run.problems if run.failures.get(p["stage"])}
        run.replans += 1
        label = f"re-plan {run.replans}: "
    run.plan = [PlanStep(stage=s, kind=k, task=_task(run, s, notes.get(s))) for s, k in steps]
    return S.ACT, label + " -> ".join(f"{s}[{k}]" for s, k in steps)


def _act(h: Harness, run: RunState, store: Checkpoints) -> tuple[S, str]:
    for step in run.plan:
        if step.done:
            continue
        stage = STAGES[step.stage]
        if step.kind in NARROW:
            stage = replace(stage, tools=NARROW[step.kind])
        attempt = run.failures.get(step.stage, 0)
        profile = route(h, step.kind, failures=attempt, run_id=run.run_id, stage=step.stage,
                        ctx_tokens=stage_ctx(h, stage.prompt, step.task, stage.tools,
                                             run.facts.get("spec_chars", 0)))
        a = h.config_agents.get(step.stage, {})
        res = run_stage(h, stage, step.task, profile=profile, max_steps=a.get("max_steps", 8),
                        max_errors=a.get("max_errors", 4), run_id=run.run_id, state=S.ACT.value,
                        check=lambda name=step.stage: CHECKS[name](run.path))
        run.stages.append({**stage_row(res), "kind": step.kind, "attempt": attempt + 1})
        if not res.ok:
            run.failures[step.stage] = attempt + 1
            store.save(run)
            return S.VERIFY, f"{step.stage} stopped ({res.stopped}) after {res.steps} steps"
        step.done = True
        store.save(run)                      # a crash after this resumes at the next step
    return S.VERIFY, "every plan step finished"


def _verify(h: Harness, run: RunState, store: Checkpoints) -> tuple[S, str]:
    run.problems = [{"stage": s, "problem": p} for s, _ in PLANS[run.task_type]
                    if (p := CHECKS[s](run.path))]
    h.log.write("verify", run_id=run.run_id, ok=not run.problems, problems=run.problems)
    if not run.problems:
        return S.DONE, "every completion check passes"
    first = f"{run.problems[0]['stage']}: {run.problems[0]['problem']}"
    if run.replans >= h.config.max_replans:
        return S.ESCALATE, f"still unfinished after {run.replans} re-plans: {first}"
    return S.PLAN, first


HANDLERS = {S.INTAKE: _intake, S.CLASSIFY: _classify, S.PLAN: _plan, S.ACT: _act, S.VERIFY: _verify}


def _escalate(h: Harness, run: RunState) -> None:
    """Safe failure: no verdict is published; a human gets the reason and the transition log."""
    run.reason = run.history[-1].reason
    h.log.write("escalate", run_id=run.run_id, course_code=run.course_code, reason=run.reason)
    lines = [f"# Escalation — {run.course_code}", "", f"**Run:** {run.run_id}  ",
             f"**Reason:** {run.reason}", "",
             "The harness stopped this review instead of publishing a verdict it could not verify. "
             "A human reviewer should finish it, or rerun it (`--mode deterministic` gives the "
             "rule-only result).", "", "## Unfinished checks",
             *([f"- {p['stage']}: {p['problem']}" for p in run.problems] or ["- (none recorded)"]),
             "", "## Transitions", *[f"- {t.src.name} -> {t.dst.name}: {t.reason}" for t in run.history], ""]
    d = ds.course_dir(run.course_code)
    d.mkdir(parents=True, exist_ok=True)
    (d / "ESCALATION.md").write_text("\n".join(lines), encoding="utf-8")


def drive(h: Harness, run: RunState, store: Checkpoints) -> dict:
    """Run handlers until DONE or ESCALATE. A state that raises escalates if the table allows it."""
    while run.state not in TERMINAL:
        try:
            nxt, reason = HANDLERS[run.state](h, run, store)
        except Exception as e:  # noqa: BLE001 - e.g. Ollama down: escalate, never crash half-done
            if S.ESCALATE not in TRANSITIONS[run.state]:
                store.save(run)
                raise
            nxt, reason = S.ESCALATE, f"{type(e).__name__}: {e}"
        advance(run, nxt, reason, store=store, log=h.log)
    if run.state is S.ESCALATE and not run.reason:
        _escalate(h, run)
        store.save(run)
    return summary(run)


def run_sm(h: Harness, path: str, *, fresh: bool = True) -> dict:
    """Review one spec with the state machine and the router."""
    _prepare(path, fresh)
    store = store_for(h)
    run = RunState(run_id=new_run_id(), path=path)
    store.save(run)
    return drive(h, run, store)


def resume(h: Harness, run_id: str) -> dict:
    """Continue a saved run from its last checkpointed state (a finished run just returns its summary)."""
    store = store_for(h)
    return drive(h, store.load(run_id), store)


def summary(run: RunState) -> dict:
    v = compute_verdict(ds.load_findings(run.course_code))
    if run.state is S.ESCALATE:
        v = {**v, "verdict": "ESCALATED"}
    return {"course_code": run.course_code, "run_id": run.run_id, "verdict": v,
            "f1_failed": _f1_failed(run.course_code), "state": run.state.value,
            "task_type": run.task_type, "classified_by": run.classified_by, "replans": run.replans,
            "stages": run.stages,
            "transitions": [f"{t.src.name} -> {t.dst.name}: {t.reason}" for t in run.history]}
