"""Review course specs with the harness (the /review-spec equivalent).

    python scripts/run_review.py courses/clean_01_data_structures.md
    python scripts/run_review.py --all
    python scripts/run_review.py --mode deterministic --all     # tools only, no Ollama
    python scripts/run_review.py --keep-findings courses/x.md   # append instead of starting fresh

Output goes to this harness's reports/ folder. Pass --reports-dir ../reports to write
where the Claude Code plugin writes (that overwrites its REVIEW_NOTE.md files).
"""
import argparse
import json

import _path  # noqa: F401

from harness import Harness, data_store as ds
from harness import pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="spec path under the plugin root")
    ap.add_argument("--all", action="store_true", help="every spec in courses/")
    ap.add_argument("--mode", choices=["agents", "deterministic"], default="agents")
    ap.add_argument("--keep-findings", action="store_true")
    ap.add_argument("--reports-dir", help="output folder (default: <harness>/reports)")
    a = ap.parse_args()
    if not a.path and not a.all:
        ap.error("give a spec path or --all")
    if a.reports_dir:
        ds.configure(reports=a.reports_dir)

    paths = ds.list_specs() if a.all else [a.path]
    h = Harness()
    run = pipeline.run_agents if a.mode == "agents" else pipeline.run_deterministic
    rows = []
    for p in paths:
        res = run(h, p, fresh=not a.keep_findings)
        c = res["verdict"]["open_counts"]
        rows.append((res["course_code"], res["verdict"]["verdict"], c))
        print(f"{res['course_code']:8} {res['verdict']['verdict']:8} "
              f"B{c['blocker']} M{c['major']} m{c['minor']}  {p}")
        for s in res["stages"]:
            print(f"    {s['stage']:20} steps={s['steps']} stopped={s['stopped']} "
                  f"tool_errors={s['tool_errors']} {s['wall_s']}s")
    if a.all:
        pipeline.finish_batch(h, paths, [r[0] for r in rows])
        print(f"\nwrote COURSE_SPEC_REVIEW.md and PROGRAM_PLO_COVERAGE.md")
    print(f"reports: {ds.reports_dir()}\nlog: {h.log.path}")


if __name__ == "__main__":
    main()
