"""M8 - Agent loop (orchestration layer, on top of the facade).

Repeats call flow B until the model stops calling tools or the step budget is spent:

    h.llm(tools) -> execute() -> tool_message() -> h.llm(tools) ...

A *stage* (see pipeline.py) fixes which tools the model is offered and which permissions
the executor grants. The loop re-checks both on every call, because a small model can
name a tool it was not offered.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from .executor import err, execute, tool_message
from .harness import Harness
from .logger import new_run_id
from .prompts import build_messages
from .tools import tool_defs


@dataclass
class Stage:
    name: str
    prompt: str                       # prompt name in prompts/, e.g. "course_reviewer"
    tools: list[str]
    allowed: frozenset[str] = frozenset({"read"})
    inject: dict = field(default_factory=dict)         # args the harness forces (not the model)
    guard: Callable[[str, dict], str | None] | None = None   # return an error string to veto


@dataclass
class AgentResult:
    stage: str
    run_id: str
    final: str
    steps: int
    calls: list[dict]                 # [{name, arguments, result}]
    stopped: str                      # "done" | "max_steps" | "repeat"
    wall_s: float = 0.0

    @property
    def errors(self) -> list[dict]:
        return [c for c in self.calls if not c["result"]["ok"]]


def run_stage(h: Harness, stage: Stage, task: str, *, profile: str = "reasoning",
              max_steps: int = 8, run_id: str | None = None) -> AgentResult:
    run_id = run_id or new_run_id()
    prompt = h.prompts.get(stage.prompt)
    msgs = build_messages(prompt.render(), user=task)
    offered = tool_defs(stage.tools)
    calls: list[dict] = []
    seen: set[str] = set()
    wall = 0.0
    for step in range(1, max_steps + 1):
        r = h.llm(profile, msgs, tools=offered, run_id=run_id, prompt_id=prompt.id)
        wall += r.wall_s
        msgs.append(r.message)
        if not r.tool_calls:
            return AgentResult(stage.name, run_id, r.content.strip(), step, calls, "done", wall)
        for call in r.tool_calls:
            f = call.setdefault("function", {})
            args = f.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            args = {**args, **{k: v for k, v in stage.inject.items()
                               if _takes(f.get("name", ""), k)}}
            f["arguments"] = args
            sig = f"{f.get('name')}:{json.dumps(args, sort_keys=True)}"
            if f.get("name") not in stage.tools:
                result = err(f"Tool {f.get('name')!r} is not available to {stage.name}. "
                             f"Available: {stage.tools}")
            elif stage.guard and (veto := stage.guard(f["name"], args)):
                result = err(veto)
            elif sig in seen:
                result = err("You already made this exact call. Use its earlier result and move on.")
            else:
                result = execute(call, allowed=set(stage.allowed), logger=h.log, run_id=run_id)
            seen.add(sig)
            calls.append({"name": f.get("name"), "arguments": args, "result": result})
            msgs.append(tool_message(call, result))
        if all(not c["result"]["ok"] and "already made" in c["result"]["error"]
               for c in calls[-len(r.tool_calls):]):
            return AgentResult(stage.name, run_id, "", step, calls, "repeat", wall)
    return AgentResult(stage.name, run_id, "", max_steps, calls, "max_steps", wall)


def _takes(tool_name: str, arg: str) -> bool:
    from .tools import TOOLS
    spec = TOOLS.get(tool_name)
    return bool(spec) and arg in spec.args.model_fields
