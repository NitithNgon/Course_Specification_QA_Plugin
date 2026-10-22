"""Review course specs with the harness (the /review-spec equivalent).

    python scripts/run_review.py courses/CPE201.md
    python scripts/run_review.py --all                         # every .md in courses/
    python scripts/run_review.py --all courses                 # every .md in a directory
    python scripts/run_review.py --mode sm courses/CPE201.md   # state machine + router (Session 3)
    python scripts/run_review.py --profile reasoning --all     # agents mode, one model for every stage
    python scripts/run_review.py --resume r-1a2b3c4d           # continue a state-machine run after a crash
    python scripts/run_review.py --mode deterministic --all    # same tools, no Ollama
    python scripts/run_review.py --keep-findings courses/x.md  # refuse instead of clearing reports/<code>/

Output goes to this harness's reports/ folder. Pass --reports-dir ../reports to write where the
Claude Code plugin writes. Each run clears reports/<code>/ first, as the plugin README requires.
"""
import argparse
from functools import partial

import _path  # noqa: F401

from harness import Harness, data_store as ds
from harness import pipeline, state_machine


def report(res: dict, path: str) -> None:
    c = res["verdict"]["open_counts"]
    print(f"{res['course_code']:8} {res['verdict']['verdict']:9} "
          f"B{c['blocker']} M{c['major']} m{c['minor']}{'  (F.1 failed)' if res['f1_failed'] else ''}  {path}")
    for s in res["stages"]:
        print(f"    {s['stage']:20} {s['profile']:10} steps={s['steps']} stopped={s['stopped']} "
              f"tool_errors={s['tool_errors']} {s['wall_s']}s")
    if "transitions" in res:
        print(f"    run {res['run_id']}  task_type={res['task_type']} ({res['classified_by']})  "
              f"re-plans={res['replans']}")
        for t in res["transitions"]:
            print(f"      {t}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="spec path under the plugin root")
    ap.add_argument("--all", nargs="?", const="", metavar="DIR", help="every .md in courses/ or in DIR")
    ap.add_argument("--mode", choices=["agents", "sm", "deterministic"], default="agents")
    ap.add_argument("--profile", help="agents mode: use this profile for every stage (single-model baseline)")
    ap.add_argument("--resume", metavar="RUN_ID", help="continue a state-machine run from its checkpoint")
    ap.add_argument("--keep-findings", action="store_true")
    ap.add_argument("--reports-dir", help="output folder (default: <harness>/reports)")
    a = ap.parse_args()
    if not a.path and a.all is None and not a.resume:
        ap.error("give a spec path, --all [DIR] or --resume RUN_ID")
    if a.profile and a.mode != "agents":
        ap.error("--profile applies to --mode agents; --mode sm picks profiles with the router")
    if a.reports_dir:
        ds.configure(reports=a.reports_dir)

    h = Harness()
    if a.resume:
        report(state_machine.resume(h, a.resume), "(resumed)")
        print(f"reports: {ds.reports_dir()}\nlog: {h.log.path}")
        return
    paths = pipeline.batch_paths(a.all or None) if a.all is not None else [a.path]
    run = {"agents": partial(pipeline.run_agents, profile=a.profile), "sm": state_machine.run_sm,
           "deterministic": pipeline.run_deterministic}[a.mode]
    codes = []
    for p in paths:
        res = run(h, p, fresh=not a.keep_findings)
        codes.append(res["course_code"])
        report(res, p)
    if a.all is not None:
        pipeline.finish_batch(h, paths, codes)
        print("\nwrote COURSE_SPEC_REVIEW.md and PROGRAM_PLO_COVERAGE.md")
    print(f"reports: {ds.reports_dir()}\nlog: {h.log.path}")


if __name__ == "__main__":
    main()
