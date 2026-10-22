"""Prefix-cache check (W11 hands-on 1, "Prefix check"): the same stage twice on one spec.

    python scripts/prefix_check.py courses/CPE201.md
    python scripts/prefix_check.py courses/CPE501.md --stage curriculum-auditor --profile fast

  A  stable prefix: same system prompt and tool list in the same order; history only appended
  B  unstable prefix: a timestamp at the top of the system prompt and the tool list shuffled
     on every call

Prints prompt_eval_duration (prompt_s), TTFT and prompt tokens per step. Expect A to get
faster after step 1 while B pays for the whole prompt every step. keep_alive in config.yaml
keeps the model (and its cache) loaded between calls. Needs Ollama.
"""
import argparse
import random
from datetime import datetime

import _path  # noqa: F401

from harness import Harness, execute, pipeline
from harness.agent_loop import run_stage


class UnstablePrefix(Harness):
    """B, what not to do: the prompt prefix changes on every call."""

    def llm(self, profile, messages, *, tools=None, **kw):
        head = {**messages[0], "content": f"Current time: {datetime.now().isoformat()}\n\n{messages[0]['content']}"}
        shuffled = random.sample(tools, len(tools)) if tools else tools
        return super().llm(profile, [head, *messages[1:]], tools=shuffled, **kw)


def run(h: Harness, path: str, stage: str, profile: str, max_steps: int):
    code = pipeline._prepare(path, fresh=True)
    if stage == "curriculum-auditor":         # the auditor starts from course-reviewer's findings
        execute({"function": {"name": "record_check_results", "arguments": {"path": path, "check": "structure"}}},
                allowed={"read", "write"})
    return run_stage(h, pipeline.STAGES[stage], pipeline.TASKS[stage].format(path=path, code=code),
                     profile=profile, max_steps=max_steps, check=lambda: pipeline.CHECKS[stage](path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="spec path under the plugin root")
    ap.add_argument("--stage", choices=["course-reviewer", "curriculum-auditor"], default="course-reviewer")
    ap.add_argument("--profile", default="reasoning")
    ap.add_argument("--max-steps", type=int, default=10)
    a = ap.parse_args()

    stable, unstable = Harness(), UnstablePrefix()
    stable.llm(a.profile, [{"role": "user", "content": "hi"}], log=False, num_predict=1)  # load the model first
    ra = run(stable, a.path, a.stage, a.profile, a.max_steps)
    rb = run(unstable, a.path, a.stage, a.profile, a.max_steps)

    print(f"{a.stage} on {a.path}, profile {a.profile}  (A run {ra.run_id}, B run {rb.run_id})")
    print(f"{'step':>4} | {'A prompt_s':>10} {'A ttft_s':>9} {'A tokens':>9} | {'B prompt_s':>10} {'B ttft_s':>9} {'B tokens':>9}")
    for i in range(max(len(ra.trace), len(rb.trace))):
        cells = []
        for r in (ra, rb):
            t = r.trace[i] if i < len(r.trace) else None
            cells.append(f"{t['prompt_s']:10.3f} {t['ttft_s']:9.3f} {t['in_tokens']:9d}" if t else f"{'':10} {'':9} {'':9}")
        print(f"{i + 1:>4} | {cells[0]} | {cells[1]}")
    for name, r in (("A", ra), ("B", rb)):
        later = [t["prompt_s"] for t in r.trace[1:]]
        print(f"{name}: steps={r.steps} stopped={r.stopped} mean prompt_s after step 1 = "
              f"{sum(later) / len(later) if later else 0:.3f}s")


if __name__ == "__main__":
    main()
