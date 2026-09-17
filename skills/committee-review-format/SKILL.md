---
name: committee-review-format
description: Use when recording findings, deciding a verdict, or writing COURSE_SPEC_REVIEW.md, a per-course review note, or an amendments-queue.csv row. Defines the shared findings schema, the deterministic verdict policy table, and the exact committee-ready output formats. Loaded by course-reviewer, curriculum-auditor, and verdict-writer.
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
    "checklist_rule": "3.3",
    "severity": "blocker",
    "section": "Section 3 -> Assessment table",
    "quote": "Midterm 30 / Final 30 / Assignment 20 / Project 15",
    "standard_ref": null,
    "message": "Assessment weights sum to 95, not 100.",
    "suggested_fix": "Increase one component by 5 points, or add a missing component, so the table sums to exactly 100.",
    "status": "open"
  }
]
```

- `severity`: one of `blocker`, `major`, `minor`.
- `standard_ref`: a citation string when curriculum-auditor produced the
  finding (e.g. `"Bloom's Taxonomy (Anderson & Krathwohl, 2001)"`,
  `"TABEE / plo-catalog.md"`); `null` for pure structural findings.
- `status`: `open` until verdict-writer (or a human) marks it `resolved`.
  **Never** delete a finding to make a verdict cleaner — mark it resolved
  with a `resolution_note`, so the audit trail stays honest.

## Deterministic verdict policy (verdict-writer MUST use this table, not judgment)

| Verdict | Trigger |
|---|---|
| **RETURN** | Any `open` finding with `severity: blocker` |
| **REVISE** | No open blockers, but ≥1 `open` finding with `severity: major` |
| **APPROVE** | No open findings with `severity: blocker` or `severity: major` (open minors are allowed, listed as advisory notes) |

This table is the entire verdict logic. If you find yourself reasoning
"but this blocker is minor in spirit" — that reasoning is exactly what the
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

## `amendments-queue.csv` row (append one row per course that is not APPROVE)

Columns, in order:
```
course_code,course_name,verdict,finding_id,severity,section,summary,suggested_fix,owner,due_date
```
`owner` is the instructor name from Section 1 if present, else
`"unassigned"`. `due_date` is left blank for a human to fill in unless the
command was given an explicit turnaround window.
