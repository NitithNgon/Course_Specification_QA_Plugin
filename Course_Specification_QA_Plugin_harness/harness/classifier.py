"""M10 - Task classifier (what is this?). Routing (who handles it?) is router.py.

Hybrid, cheapest first:
  1 rules        form fields: the F.1 form gate and the CLO verb derivation. They decide
                 every document they can parse
  2 small model  the "classify" route (fast profile), enum schema, when the rules cannot decide
  3 main LLM     the router's default profile, last resort
  -> None        the caller escalates

A model answer is validated twice, as in M5: the schema (a Literal enum) and a domain rule
(it may not contradict the form gate). One repair attempt per profile.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import qa_rules as rules
from .harness import Harness
from .prompts import build_messages
from .qa_tools import _code, _load, _overrides
from .router import route

TaskType = Literal["off_form", "standard", "needs_judgment"]


class TaskClass(BaseModel):
    """The CLASSIFY output schema."""
    model_config = ConfigDict(extra="forbid")
    task_type: TaskType
    reason: str = Field(min_length=3, max_length=300)


def facts_of(path: str) -> dict:
    """What the classifier looks at, read from the spec by code (INTAKE)."""
    spec, p = _load(path)
    code = _code(spec, p)
    lv = rules.clo_levels(spec, _overrides(code))
    missing = rules.form_gate(spec)
    return {"course_code": code, "course_title": spec.course_title,
            "on_official_form": not missing, "form_gate_missing": missing,
            "clos": len(spec.clos), "methods": len(spec.methods),
            "needs_judgment": [c.id for c in spec.clos
                               if not lv[c.id]["classifiable"] and not lv[c.id].get("override")],
            "spec_chars": len(p.read_text(encoding="utf-8"))}


def by_rules(facts: dict) -> TaskClass | None:
    if not facts["on_official_form"]:
        return TaskClass(task_type="off_form",
                         reason="form gate: missing " + "; ".join(facts["form_gate_missing"]))
    if not facts["clos"] or not facts["methods"]:
        return None            # on the form, but no CLO or assessment rows parsed: rules cannot tell
    if facts["needs_judgment"]:
        ids = facts["needs_judgment"]
        return TaskClass(task_type="needs_judgment",
                         reason=f"{', '.join(ids)} {'has' if len(ids) == 1 else 'have'} no classified student verb")
    return TaskClass(task_type="standard", reason="every CLO verb is classified by bloom-taxonomy.md")


def classify(h: Harness, facts: dict, *, run_id: str | None = None) -> tuple[TaskClass | None, str]:
    """Return (task class or None, how it was decided)."""
    c, how = by_rules(facts), "rules"
    if c is None:
        tried = []
        for profile, how in ((route(h, "classify", run_id=run_id), "small model"),
                             (h.config.routing.default, "main LLM")):
            if profile in tried:
                continue
            tried.append(profile)
            if c := _ask(h, profile, facts, run_id):
                break
        else:
            how = "undecided"
    h.log.write("classify", run_id=run_id, method=how, task_type=c.task_type if c else None,
                reason=c.reason if c else None)
    return c, how


def _ask(h: Harness, profile: str, facts: dict, run_id: str | None) -> TaskClass | None:
    prompt = h.prompts.get("classify_task")
    msgs = build_messages(prompt.render(), user=json.dumps(facts, ensure_ascii=False))
    for attempt in range(2):
        r = h.llm(profile, msgs, schema=TaskClass.model_json_schema(), log=False)
        try:
            c = TaskClass.model_validate_json(r.content)
            if (c.task_type == "off_form") == facts["on_official_form"]:
                raise ValueError(f"task_type {c.task_type!r} contradicts the form gate "
                                 f"(on_official_form={facts['on_official_form']})")
        except ValueError as e:              # pydantic's ValidationError is a ValueError
            error = str(e)[:300]
            h.log.llm_call(run_id=run_id, profile=profile, result=r, prompt_id=prompt.id,
                           valid=False, error=error, retry=attempt, state="classify")
            msgs = msgs + [{"role": "assistant", "content": r.content},
                           {"role": "user", "content": f"Invalid output: {error}. "
                                                       "Fix it and return JSON only, matching the schema."}]
            continue
        h.log.llm_call(run_id=run_id, profile=profile, result=r, prompt_id=prompt.id,
                       valid=True, retry=attempt, state="classify")
        return c
    return None
