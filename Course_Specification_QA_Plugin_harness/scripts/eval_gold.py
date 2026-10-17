"""Score the deterministic tool pipeline (or the agent pipeline) against courses/gold-labels.json.

    python scripts/eval_gold.py                    # tools only: verdict, weight sum, false-blocker rate
    python scripts/eval_gold.py --mode agents      # model chooses the tool calls (needs Ollama)
    python scripts/eval_gold.py --mode agents --repeats 5    # verdict consistency
    python scripts/eval_gold.py --mode agents --cases clean_01_data_structures.md,blocker_02_weight_95.md

Runs in a scratch copy of the plugin root. The gold file is read here, never by an agent.
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

import _path  # noqa: F401

from harness import Harness, data_store as ds, pipeline
from harness.qa_tools import _spec
from harness.qa_rules import weight_report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["deterministic", "agents"], default="deterministic")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--cases", help="comma-separated gold file names (default: all)")
    a = ap.parse_args()

    gold_src = ds.root() / "courses" / "gold-labels.json"
    gold = json.loads(gold_src.read_text(encoding="utf-8"))["cases"]
    if a.cases:
        gold = [g for g in gold if g["file"] in a.cases.split(",")]
    tmp = Path(tempfile.mkdtemp(prefix="qa_eval_"))
    for d in ("courses", "references"):
        shutil.copytree(ds.root() / d, tmp / d)
    ds.configure(tmp)
    h = Harness(log_file=tmp / "calls.jsonl")
    run = pipeline.run_agents if a.mode == "agents" else pipeline.run_deterministic

    stage_rows = []
    hits = false_blockers = clean = 0
    print(f"{'file':34} {'gold':8} {'got':8} {'sum':>5}  runs-matching")
    for g in gold:
        path = f"courses/{g['file']}"
        results = [run(h, path) for _ in range(a.repeats)]
        verdicts = [r["verdict"]["verdict"] for r in results]
        stage_rows += [(g["file"], s) for r in results for s in r["stages"]]
        got = verdicts[0]
        wsum = weight_report(_spec(path))["sum"]
        blockers = ds.load_findings(g["course_code"])
        n_block = sum(1 for f in blockers if f["severity"] == "blocker")
        ok = got == g["expected_verdict"] and wsum == g["expected_weight_sum"]
        hits += ok
        if g["category"] == "clean":
            clean += 1
            false_blockers += n_block > 0
        match = sum(v == g["expected_verdict"] for v in verdicts)
        print(f"{g['file']:34} {g['expected_verdict']:8} {got:8} {wsum:5g}  "
              f"{match}/{a.repeats} {'OK' if ok else 'MISS'}")
    for f, s in stage_rows:
        print(f"  {f:34} {s['stage']:20} steps={s['steps']} stopped={s['stopped']} "
              f"tool_errors={s['tool_errors']} {s['wall_s']}s")
    print(f"\nverdict+weight match:{hits}/{len(gold)}   false-blocker rate: {false_blockers}/{clean}")
    print(f"mode={a.mode}  scratch={tmp}")


if __name__ == "__main__":
    main()
