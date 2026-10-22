"""Score a harness run against the plugin's ground truth in evaluation/ (README "Scoring a take").

    python scripts/eval_ground_truth.py                          # tools only, all 11 courses
    python scripts/eval_ground_truth.py --mode agents            # model chooses the tool calls (Ollama)
    python scripts/eval_ground_truth.py --mode agents --repeats 3 --courses CPE201,CPE502
    python scripts/eval_ground_truth.py -v                       # list misses and false positives

Session 3 comparison (same tasks, same scoring), slide "HANDS-ON: State machine + router":
    python scripts/eval_ground_truth.py --mode agents --profile reasoning   # single-model loop
    python scripts/eval_ground_truth.py --mode sm                            # state machine + router

Runs in a scratch copy of the plugin WITHOUT evaluation/, as the plugin README asks, so no
stage can read the answers. Also checks the batch PLO rollup against evaluation/README.md.
A model run ends with one comparison line: task success (verdict right, no miss, no false
positive), mean steps, mean wall time, tool-call success, model switches and load time,
re-plans and escalations.
"""
import argparse
import re
import shutil
import tempfile
from collections import Counter
from functools import partial
from pathlib import Path

import _path  # noqa: F401

from harness import Harness, data_store as ds, ground_truth as gt, pipeline, state_machine
from harness.qa_rules import weight_report
from harness.qa_tools import _coverage, _load


def expected_rollup(readme: Path) -> dict[str, str]:
    t = readme.read_text(encoding="utf-8").split("## Expected batch PLO rollup", 1)[1]
    return {m[1]: m[2].strip() for m in re.finditer(r"^\|\s*(PLO\d+)\s*\|.*\|\s*([^|]+?)\s*\|\s*$", t, re.M)}


def run_metrics(res: dict, score: dict) -> dict:
    """One task's row for the comparison table (slide M20 metrics)."""
    st = res["stages"]
    profiles = [s["profile"] for s in st]
    return {"success": score["verdict_ok"] and not score["misses"] and not score["false_positives"],
            "steps": sum(s["steps"] for s in st), "wall_s": sum(s["wall_s"] for s in st),
            "tool_calls": sum(s["tool_calls"] for s in st), "tool_errors": sum(s["tool_errors"] for s in st),
            "switches": sum(a != b for a, b in zip(profiles, profiles[1:])),
            "load_s": sum(s["load_s"] for s in st), "replans": res.get("replans", 0),
            "escalated": res.get("state") == "escalate"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["deterministic", "agents", "sm"], default="deterministic")
    ap.add_argument("--profile", help="agents mode: one profile for every stage (single-model baseline)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--courses", help="comma-separated course codes (default: all)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.profile and a.mode != "agents":
        ap.error("--profile applies to --mode agents; --mode sm picks profiles with the router")

    plugin = ds.root()
    truth = gt.load_all(plugin / "evaluation")
    rollup = expected_rollup(plugin / "evaluation" / "README.md")
    if a.courses:
        truth = {k: v for k, v in truth.items() if k in a.courses.split(",")}

    tmp = Path(tempfile.mkdtemp(prefix="qa_eval_"))
    for d in ("courses", "references", "hooks"):
        shutil.copytree(plugin / d, tmp / d, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    ds.configure(tmp)                        # no evaluation/ in the scratch copy
    h = Harness(log_file=tmp / "calls.jsonl")
    run = {"agents": partial(pipeline.run_agents, profile=a.profile), "sm": state_machine.run_sm,
           "deterministic": pipeline.run_deterministic}[a.mode]

    tot = Counter()
    stage_rows, runs = [], []
    print(f"{'course':7} {'gold':8} {'got':8} {'runs ok':8} {'hits':>6} {'dup':>4} {'FP':>3}  weight")
    for code, t in truth.items():
        path = f"courses/{code}.md"
        verdicts, last = [], None
        for _ in range(a.repeats):
            res = run(h, path)
            verdicts.append(res["verdict"]["verdict"])
            stage_rows += [(code, s) for s in res["stages"]]
            last = gt.score(t, ds.load_findings(code), verdicts[-1])
            runs.append(run_metrics(res, last))
        spec, _ = _load(path)
        w = weight_report(spec)["sum"] if spec.methods else None
        w_ok = t.weight_sum is None or w == t.weight_sum
        ok_runs = sum(v == t.verdict for v in verdicts)
        print(f"{code:7} {t.verdict:8} {verdicts[-1]:8} {ok_runs}/{a.repeats:<6} "
              f"{last['hits']:>3}/{last['expected']:<2} {last['duplicates']:>4} {len(last['false_positives']):>3}  "
              f"{w if w is not None else '-'}{'' if w_ok else ' (expected ' + str(t.weight_sum) + ')'}")
        if a.verbose:
            for m in last["misses"]:
                print(f"        miss: {m}")
            for f in last["false_positives"]:
                print(f"        false positive: {f}")
        tot.update(verdict_ok=last["verdict_ok"], hits=last["hits"], expected=last["expected"],
                   fp=len(last["false_positives"]), dupes=last["duplicates"], courses=1,
                   consistent=len(set(verdicts)) == 1,
                   rule_ok=last["rule_accuracy"][0], sev_ok=last["severity_accuracy"][0],
                   false_blockers=(t.verdict == "APPROVE") * sum(
                       1 for f in ds.load_findings(code) if f["severity"] == "blocker" and f["status"] == "open"))

    for code, s in stage_rows:
        print(f"  {code:7} {s['stage']:20} {s['profile']:10} steps={s['steps']} stopped={s['stopped']} "
              f"tool_errors={s['tool_errors']} {s['wall_s']}s")
    print(f"\nverdicts {tot['verdict_ok']}/{tot['courses']} | findings hit {tot['hits']}/{tot['expected']} "
          f"(rule ok {tot['rule_ok']}, severity ok {tot['sev_ok']}) | duplicates {tot['dupes']} | "
          f"false positives {tot['fp']} | false blockers on APPROVE courses {tot['false_blockers']} | "
          f"consistent across repeats {tot['consistent']}/{tot['courses']}")
    if not a.courses:
        got = {r["plo"]: r["status"] for r in _coverage([f"courses/{c}.md" for c in truth])}
        bad = {p: (got.get(p), s) for p, s in rollup.items() if got.get(p) != s}
        print(f"PLO rollup: {len(rollup) - len(bad)}/{len(rollup)} match evaluation/README.md"
              + ("" if not bad else f"  mismatches: {bad}"))
    if a.mode != "deterministic":
        n, m = len(runs), Counter()
        for r in runs:
            m.update(r)
        print(f"{a.mode}{'/' + a.profile if a.profile else ''}: task success {m['success']}/{n} | "
              f"mean steps {m['steps'] / n:.1f} | mean wall {m['wall_s'] / n:.1f}s | "
              f"tool calls ok {m['tool_calls'] - m['tool_errors']}/{m['tool_calls']} | "
              f"model switches {m['switches']} | load {m['load_s']:.1f}s | "
              f"re-plans {m['replans']} | escalated {m['escalated']}")
    print(f"mode={a.mode}  scratch={tmp}")


if __name__ == "__main__":
    main()
