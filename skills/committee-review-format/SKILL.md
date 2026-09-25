---
name: committee-review-format
description: Use when recording findings, deciding a verdict, or writing COURSE_SPEC_REVIEW.md, a per-course review note, or a reports/amendments-queue.csv row. Defines the shared findings schema, the deterministic verdict policy table, and the exact committee-ready output formats. Loaded by course-reviewer, curriculum-auditor, and verdict-writer.
---

# Committee Review Format — shared schema and templates

## `reports/<course_code>/findings.json` schema

A JSON array, appended to (never overwritten) by course-reviewer and
curriculum-auditor:

```json
[
  {
    "id": "F001",
    "source_agent": "course-reviewer",
    "checklist_rule": "4.3",
    "severity": "blocker",
    "section": "Assessment table",
    "quote": "| Project | Bloom's taxonomy (Create) | CLO3 | 15.00 |",
    "standard_ref": null,
    "message": "Assessment weights sum to 95 (30 + 30 + 20 + 15), not 100: short by 5.",
    "suggested_fix": "Raise one component by 5 points, or add the missing component to the table, so the weights sum to exactly 100.",
    "status": "open"
  }
]
```

- `checklist_rule`: a rule ID from `references/checklist.md`.
- `severity`: `blocker`, `major` or `minor` — exactly the severity the
  checklist gives that rule.
- `source_agent`: the rule's Owner in the checklist (`course-reviewer` or
  `curriculum-auditor`).
- `section`: a pointer precise enough to find the row; `quote`: the text as
  printed, the `-` as printed, or `"(absent)"` for a missing section.
- `standard_ref`: a citation string when curriculum-auditor produced the
  finding (e.g. `"Bloom's Taxonomy (Anderson & Krathwohl, 2001)"`,
  `"plo-catalog.md"`); `null` for structural findings.
- `status`: `open` until a human reviewer marks it `resolved` with a
  `resolution_note`. **Never** delete a finding to make a verdict cleaner;
  the audit trail stays honest.
- One finding per failing row or field (`checklist.md`, "Findings
  granularity").

The `validate_findings.py` PreToolUse hook enforces this schema on every
write: it blocks a missing field, a rule not in the checklist, a severity or
source agent that differs from the checklist, a resolved finding without a
note, and any change to or removal of an existing finding.

## Deterministic verdict policy (verdict-writer MUST use this table, not judgment)

| Verdict | Trigger |
|---|---|
| **RETURN** | Any `open` finding with `severity: blocker` |
| **REVISE** | No open blockers, but ≥1 `open` finding with `severity: major` |
| **APPROVE** | No open findings with `severity: blocker` or `severity: major` (open minors are allowed, listed as advisory notes) |

This table is the entire verdict logic. If you find yourself reasoning
"but this blocker is minor in spirit", that reasoning is what the
PreToolUse hook exists to override. Do not talk yourself into APPROVE with
an open blocker; write REVISE or RETURN and let the instructor fix the
underlying finding instead.

## `COURSE_SPEC_REVIEW.md` (batch summary, one per `/review-spec` run)

```markdown
# Course Spec Review — <run date>

| Course Code | Course Name | Verdict | Blockers | Majors | Minors |
|---|---|---|---|---|---|
| CPE101 | ... | APPROVE | 0 | 0 | 1 |
| CPE202 | ... | RETURN  | 2 | 0 | 0 |

See `reports/<course_code>/REVIEW_NOTE.md` for per-course detail.
See `reports/PROGRAM_PLO_COVERAGE.md` for the batch PLO coverage rollup (batch mode only).
```

## `reports/<course_code>/REVIEW_NOTE.md` (per-course, instructor-facing)

```markdown
# Review Note — <Course Code>: <Course Name>

**Verdict:** APPROVE | REVISE | RETURN

## Findings

### [BLOCKER] <checklist_rule> — <section>
> <quote>

<message>

**Fix:** <suggested_fix>

(repeat per finding, blockers first, then majors, then minors)

## Standards cited
- <standard_ref list, deduplicated>
```

The `**Verdict:** X` line must appear exactly once, in that exact format
(`**Verdict:** ` followed immediately by one of `APPROVE`, `REVISE`,
`RETURN` in caps) — the PreToolUse hook pattern-matches this literal string.
Do not paraphrase it, translate it, or add extra words on that line.

## `reports/amendments-queue.csv` row (one row per open finding of a course that is not APPROVE)

The path is exactly `reports/amendments-queue.csv` — one file for the whole
run, alongside `reports/audit-log.jsonl`. Never write it to the repository
root and never create a per-course copy: a split queue means an instructor
fixing one file silently misses rows written to the other.

Columns, in order:
```
course_code,course_name,verdict,finding_id,severity,section,summary,suggested_fix,owner,due_date
```
Write the header row only when creating the file; append rows without a
header when it already exists.
`owner` is the course coordinator named on the form; if none is named, the
first listed instructor; if neither, `"unassigned"`. `due_date` is left
blank for a human to fill in unless the command was given an explicit
turnaround window.
