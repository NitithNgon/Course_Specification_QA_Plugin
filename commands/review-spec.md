---
description: Review one or more course specifications end to end (course-reviewer -> curriculum-auditor -> verdict-writer) and produce committee-ready output.
argument-hint: "[path to .md or .pdf | --all [directory]]"
allowed-tools: Read, Grep, Glob, Write
---

Review the course specification(s) at: $ARGUMENTS

What is in scope:

- A single path: review that file, Markdown or PDF, wherever it is.
- `--all`: review every `.md` file in `courses/` as one batch.
- `--all <directory>`: review every `.md` and `.pdf` file in that directory
  as one batch (for example `--all total-cases` for the real syllabi).

Never review files under `evaluation/` (the ground truth) or `reports/`
(generated output), even when a pattern would match them.

For each specification in scope, run this pipeline **in order** — do not
parallelize the stages of one specification, since curriculum-auditor
depends on course-reviewer's extraction and verdict-writer depends on both:

1. Invoke the `course-reviewer` subagent on the file. Wait for it to report
   the course code, finding counts, weight sum and difference from 100, and
   whether the form gate (F.1) failed. If it reports that
   `reports/<course_code>/findings.json` already existed from an earlier
   run, stop for that course and tell the user to clear
   `reports/<course_code>/` first: the earlier run's open findings would
   otherwise count in this verdict.
2. Unless course-reviewer reported that F.1 failed, invoke the
   `curriculum-auditor` subagent with the course code and file path (and,
   in batch mode, the full list of course codes, so it writes
   `reports/PROGRAM_PLO_COVERAGE.md` after the last course).
3. Invoke the `verdict-writer` subagent with the course code(s) to write
   `reports/<course_code>/REVIEW_NOTE.md`, update
   `reports/COURSE_SPEC_REVIEW.md`, and append any needed
   `reports/amendments-queue.csv` rows.

After the pipeline completes for every specification in scope, report a
short summary table: course code, verdict, blocker/major/minor counts, and
the path to each `REVIEW_NOTE.md`. Say explicitly if any `Write` or `Edit`
was blocked by a PreToolUse hook during the run — `block_approve_with_blocker`
(an APPROVE with an open blocker) or `validate_findings` (a finding that
breaks the checklist). A blocked write is a signal worth surfacing, not one
to retry around.
