"""Review course specs with the harness (the /review-spec equivalent).

    python scripts/run_review.py courses/CPE201.md
    python scripts/run_review.py --all                         # every .md in courses/
    python scripts/run_review.py --all courses                 # every .md in a directory
    python scripts/run_review.py --mode deterministic --all    # same tools, no Ollama
    python scripts/run_review.py --keep-findings courses/x.md  # refuse instead of clearing reports/<code>/

Output goes to this harness's reports/ folder. Pass --reports-dir ../reports to write where the
Claude Code plugin writes. Each run clears reports/<code>/ first, as the plugin README requires.
"""
import argparse

import _path  # noqa: F401

from harness import Harness, data_store as ds
from harness import pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="spec path under the plugin root")
    ap.add_argument("--all", nargs="?", const="", metavar="DIR", help="every .md in courses/ or in DIR")
    ap.add_argument("--mode", choices=["agents", "deterministic"], default="agents")
    ap.add_argument("--keep-findings", action="store_true")
    ap.add_argument("--reports-dir", help="output folder (default: <harness>/reports)")
    a = ap.parse_args()
    if not a.path and a.all is None:
        ap.error("give a spec path or --all [DIR]")
    if a.reports_dir:
        ds.configure(reports=a.reports_dir)

    paths = pipeline.batch_paths(a.all or None) if a.all is not None else [a.path]
    h = Harness()
    run = pipeline.run_agents if a.mode == "agents" else pipeline.run_deterministic
    codes = []
    for p in paths:
        res = run(h, p, fresh=not a.keep_findings)
        c = res["verdict"]["open_counts"]
        codes.append(res["course_code"])
        print(f"{res['course_code']:8} {res['verdict']['verdict']:8} "
              f"B{c['blocker']} M{c['major']} m{c['minor']}{'  (F.1 failed)' if res['f1_failed'] else ''}  {p}")
        for s in res["stages"]:
            print(f"    {s['stage']:20} steps={s['steps']} stopped={s['stopped']} "
                  f"tool_errors={s['tool_errors']} {s['wall_s']}s")
    if a.all is not None:
        pipeline.finish_batch(h, paths, codes)
        print("\nwrote COURSE_SPEC_REVIEW.md and PROGRAM_PLO_COVERAGE.md")
    print(f"reports: {ds.reports_dir()}\nlog: {h.log.path}")


if __name__ == "__main__":
    main()
