"""M8 - Agent loop (orchestration layer, on top of the facade).

Repeats call flow B until the model stops calling tools or a stop condition fires:

    h.llm(tools) -> execute() -> tool_message() -> h.llm(tools) ...

A *stage* (see pipeline.py) fixes which tools the model is offered and which permissions
the executor grants. The loop re-checks both on every call, because a small model can
name a tool it was not offered.

Stop conditions (W11 slides "The agent loop" and "How small models fail in loops"):
  done          no tool call AND the completion check passes. If the check fails, the loop
                says what is missing, restates the goal and keeps going (stops too early,
                loses the goal)
  max_steps     out of steps                                 -> safe failure, logged
  repeat        every call in a step repeated an earlier one -> safe failure, logged
  error_budget  too many failed tool calls in this stage     -> safe failure, logged
Repeats are answered with an error observation, never executed again.

When a limit ends the loop, the completion check still runs once: if the work is verifiably
done (e.g. everything was recorded, then the model looped), the stage is `verified` and no
safe failure is logged. `stopped` keeps the real stop reason for the experiment metrics.
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

REPEAT = "You already made this exact call. Use its earlier result and move on."


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
    stopped: str                      # "done" | "max_steps" | "repeat" | "error_budget"
    wall_s: float = 0.0
    profile: str = ""
    trace: list[dict] = field(default_factory=list)    # one row per LLM call (latency, tokens)
    verified: bool | None = None      # last completion check; None when the stage has none

    @property
    def errors(self) -> list[dict]:
        return [c for c in self.calls if not c["result"]["ok"]]

    @property
    def ok(self) -> bool:
        return self.verified if self.verified is not None else self.stopped == "done"


def run_stage(h: Harness, stage: Stage, task: str, *, profile: str = "reasoning",
              max_steps: int = 8, max_errors: int = 4, check: Callable[[], str | None] | None = None,
              run_id: str | None = None, state: str | None = None) -> AgentResult:
    """Run one stage to a stop condition. `check` returns what is still missing, or None when done."""
    run_id = run_id or new_run_id()
    prompt = h.prompts.get(stage.prompt)
    msgs = build_messages(prompt.render(), user=task)
    offered = tool_defs(stage.tools)
    tag = {"stage": stage.name, **({"state": state} if state else {})}
    calls: list[dict] = []
    trace: list[dict] = []
    seen: set[str] = set()
    errors = 0

    def stop(stopped: str, steps: int, final: str = "") -> AgentResult:
        verified = None if check is None else stopped == "done" or not check()
        if stopped != "done" and verified:
            h.log.write("completion_check", run_id=run_id, step=steps, ok=True, missing=None,
                        after=stopped, **tag)
        elif stopped != "done":
            h.log.write("safe_failure", run_id=run_id, reason=stopped, steps=steps,
                        tool_errors=errors, **tag)
        return AgentResult(stage.name, run_id, final, steps, calls, stopped,
                           sum(t["wall_s"] for t in trace), profile, trace, verified)

    for step in range(1, max_steps + 1):
        r = h.llm(profile, msgs, tools=offered, run_id=run_id, prompt_id=prompt.id,
                  log_extra={"step": step, **tag})
        trace.append({"step": step, "profile": profile, "in_tokens": r.prompt_tokens,
                      "load_s": r.load_s, "prompt_s": r.prompt_s, "ttft_s": r.ttft_s,
                      "wall_s": r.wall_s, "tool_calls": len(r.tool_calls)})
        msgs.append(r.message)
        if not r.tool_calls:
            missing = check() if check else None
            if check:
                h.log.write("completion_check", run_id=run_id, step=step, ok=not missing,
                            missing=missing, **tag)
            if not missing:
                return stop("done", step, r.content.strip())
            msgs.append({"role": "user", "content": f"Not finished: {missing}\nGoal: {task}"})
            continue
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
                result = err(REPEAT)
            else:
                result = execute(call, allowed=set(stage.allowed), logger=h.log, run_id=run_id)
            seen.add(sig)
            errors += not result["ok"]
            calls.append({"name": f.get("name"), "arguments": args, "result": result})
            msgs.append(tool_message(call, result))
        if errors >= max_errors:
            return stop("error_budget", step)
        if all(not c["result"]["ok"] and c["result"]["error"] == REPEAT
               for c in calls[-len(r.tool_calls):]):
            return stop("repeat", step)
    return stop("max_steps", max_steps)


def _takes(tool_name: str, arg: str) -> bool:
    from .tools import TOOLS
    spec = TOOLS.get(tool_name)
    return bool(spec) and arg in spec.args.model_fields
