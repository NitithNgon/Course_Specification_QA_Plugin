---
name: course-qa-checklist
description: Use when reviewing a course specification's structural completeness — whether every mandatory section, CLO field, assessment weight, and policy statement is present and well-formed. Loaded by course-reviewer.
---

# Course QA Checklist — methodology

Source of truth: `${CLAUDE_PLUGIN_ROOT}/references/checklist.md`. Read that
file first; it is the actual checklist. This skill is the *method* for
applying it, not the checklist itself.

## Method

1. Parse the course spec into its four sections (Course Information,
   Learning Outcomes, Assessment, Course Policies). If a whole section is
   missing or the document doesn't follow the template at all (see the real
   `total-cases/2110514.pdf` and `2110555.pdf` examples — free-text syllabi
   with no CLO/PLO table), do **not** guess a mapping. Record a single
   high-severity finding: "document does not follow the course-spec
   template; sections X, Y, Z could not be located" and stop deeper checks
   for the missing sections — a false "PASS" on a section that doesn't
   exist is worse than an honest "cannot evaluate."
2. Walk `checklist.md` item by item against what you actually parsed.
3. For every FAIL, record a finding with **all four** of:
   - `section`: exact pointer (e.g. "Section 3 → Assessment table → row
     'Final Exam'")
   - `quote`: the verbatim text found (or `"(absent)"` if nothing is there)
   - `rule`: which checklist item number failed
   - `suggested_fix`: a concrete, one-sentence fix an instructor could act
     on without asking a follow-up question — never "improve PLO mapping,"
     always "add PLO code (e.g. PLO3) to CLO2, referencing
     references/plo-catalog.md"
4. Compute the raw assessment-weight sum yourself (do the arithmetic, don't
   estimate) and report both the sum and the delta from 100 explicitly —
   e.g. "sum = 95, short by 5" — this is what the Weight Integrity metric
   scores against.
5. Do not classify Bloom levels or validate PLO codes here — that is
   `curriculum-auditor`'s job (`bloom-verb-rules`, `plo-mapping-standard`
   skills). This skill only checks *presence and structural well-formedness*,
   not domain correctness.
6. Assign the severity given in `checklist.md`'s "Severity defaults" table
   unless a later human override exists — never invent your own severity
   scale per-run, that is what breaks the verdict-consistency metric.
7. Write (or append to) `reports/<course_code>/findings.json` — see
   `committee-review-format` skill for the exact schema.
