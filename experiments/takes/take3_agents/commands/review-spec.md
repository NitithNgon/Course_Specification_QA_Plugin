---
description: Review one or more course specifications end to end (course-reviewer -> curriculum-auditor -> verdict-writer) and produce committee-ready output.
argument-hint: "[path-to-course-spec | --all]"
allowed-tools: Read, Grep, Glob, Write
---

Review the course specification(s) at: $ARGUMENTS

If the argument is `--all`, process every file under `courses/` (excluding
`courses/gold-labels.json` and any `_gold`/dotfile paths) as one batch run;
otherwise treat the argument as a single file path under `courses/`.

For each course spec in scope, run this pipeline **in order** — do not
parallelize across stages within a single course, since curriculum-auditor
depends on course-reviewer's extraction and verdict-writer depends on both:

1. Invoke the `course-reviewer` subagent on the file. Wait for it to report
   back the course code, finding counts, and weight-sum delta.
2. Unless course-reviewer explicitly reported that the document was too
   structurally broken to extract any CLOs/PLOs at all, invoke the
   `curriculum-auditor` subagent with the course code (and, in `--all` mode,
   the full list of course codes in this batch, so it can also produce the
   program-level PLO coverage rollup after the last course).
3. Invoke the `verdict-writer` subagent with the course code(s) to produce
   `REVIEW_NOTE.md`, update `COURSE_SPEC_REVIEW.md`, and append any needed
   `amendments-queue.csv` rows.

After the pipeline completes for all courses in scope, report a short
summary table to the user: course code, verdict, blocker/major/minor
counts, and the path to each `REVIEW_NOTE.md`. Point out explicitly if any
`Write` call was blocked by the PreToolUse hook during this run (check for
a hook denial in the tool results) — that's a signal worth surfacing, not
silently retrying around.
