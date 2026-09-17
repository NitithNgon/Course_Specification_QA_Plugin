# Take 3/4 (real pipeline: course-reviewer -> curriculum-auditor -> verdict-writer, hook live) — Case B (missing sections, CPE599)

Condition: the actual production path — three separate subagents, real
Write calls to reports/CPE599/findings.json and REVIEW_NOTE.md, PreToolUse
hook genuinely live on both writes.

## Result

course-reviewer: applied SKILL.md step 1 literally ("If a whole section is
missing... record a single high-severity finding... stop deeper checks") ->
ONE blocker-level finding (F001, "Section 4 entirely missing," bundling all
5 sub-items into one entry) + one minor (F002, rubric missing).
curriculum-auditor: 0 new findings (Bloom/PLO all clean, confirmed
independently).

**Findings: 1 blocker / 0 major / 1 minor.**
**Verdict: RETURN** (policy table: any open blocker -> RETURN, overrides
everything else including the clean curriculum audit).

Outputs written for real: reports/CPE599/findings.json, REVIEW_NOTE.md,
reports/COURSE_SPEC_REVIEW.md (appended CPE599 row alongside the existing
CPE201 row). No PreToolUse hook denial this run (verdict RETURN is
consistent with the open blocker, so nothing to block).

BUG FOUND: verdict-writer created a NEW `reports/amendments-queue.csv` for
the 2 CPE599 rows, instead of appending to the project's existing
root-level `amendments-queue.csv` (which the README's layout diagram
documents as the canonical location, and which already existed with just a
header row). This is a real path-convention bug in verdict-writer's
behavior, not an experimental artifact -- confirmed by diffing both files
after the run.

## Cross-take comparison for Case B (all facts, no gold file needed)

| Take | Method | Blocker | Major | Minor | Verdict |
|---|---|---|---|---|---|
| 0 (baseline) | freeform, no checklist | 3 (2 hallucinated) | 2 (hallucinated) | 1 | RETURN |
| 1 (+Skill, single agent) | decomposed per-item | 0 | 2 | 4 | REVISE |
| 2 (+Command wording, single agent) | decomposed per-item | 0 | 2 | 4 | REVISE |
| 3/4 (real pipeline, hook live) | aggregated whole-section | 1 | 0 | 1 | RETURN |

Verdict is NOT monotonically stabilizing across takes for this case. Takes
1 and 2 agree with each other (REVISE) via one reading of
skills/course-qa-checklist/SKILL.md; the real pipeline (Take 3/4) agrees
with the *baseline's top-line category* (RETURN) via a different, equally
textually-supported reading of the same skill file. This is a genuine,
reproducible internal ambiguity (SKILL.md step 1 "aggregate" vs step 6 "use
checklist.md's per-item severities"), not model noise -- both single-agent
conditions independently chose decomposition, and the one real course-
reviewer run chose aggregation, consistent with which instruction it
weighted more heavily.

Practical consequence: whether this course spec gets RETURNed to the
instructor (rewrite-and-resubmit) or REVISEd (fix two specific policy
statements) depends on which reading the pipeline happens to apply -- a
real committee-facing inconsistency worth fixing in SKILL.md before
production use (e.g., "record one blocker-tier finding AND still enumerate
the per-item severities underneath it for the amendments queue" would
resolve both instructions without contradiction).
