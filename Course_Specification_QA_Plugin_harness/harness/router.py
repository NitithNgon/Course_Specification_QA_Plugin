"""M11 - Model router (who handles it?). Task classification (M10) is a separate decision.

Rule-based, from the `routing:` block in config.yaml:

    profile = routes[kind] (else default)
    if estimated prompt > ctx_ratio x num_ctx of that profile: profile = long_context
    if failures >= fallback_after: move up the ladder one rung per fallback_after failures

Every decision is one "route" line in logs/calls.jsonl: it is a variable in the experiment.
"""
from __future__ import annotations

import json

from .harness import Harness
from .tools import tool_defs

CHARS_PER_TOKEN = 4          # rough estimate for English text and JSON


def estimate_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // CHARS_PER_TOKEN


def stage_ctx(h: Harness, prompt: str, task: str, tools: list[str], spec_chars: int) -> int:
    """Estimated prompt size for a stage: system prompt + task + tool list + the spec its tools return."""
    return estimate_tokens(h.prompts.get(prompt).render(), task, json.dumps(tool_defs(tools))) \
        + spec_chars // CHARS_PER_TOKEN


def route(h: Harness, kind: str, *, ctx_tokens: int = 0, failures: int = 0,
          run_id: str | None = None, **context) -> str:
    r = h.config.routing
    profile = r.routes.get(kind, r.default)
    rule = "table" if kind in r.routes else "default"
    num_ctx = h.config.profile(profile).options.get("num_ctx")
    if num_ctx and ctx_tokens > num_ctx * r.ctx_ratio:
        profile, rule = r.long_context, "long_context"
    if failures >= r.fallback_after:
        up = failures // r.fallback_after
        stronger = r.ladder[min(len(r.ladder) - 1, r.ladder.index(profile) + up)] \
            if profile in r.ladder else r.ladder[-1]
        profile, rule = stronger, f"{rule}+fallback"
    h.log.write("route", run_id=run_id, kind=kind, profile=profile, rule=rule,
                ctx_tokens=ctx_tokens, failures=failures, **context)
    return profile
