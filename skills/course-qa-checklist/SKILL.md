---
name: course-qa-checklist
description: Use when reviewing a course specification's structure, completeness and arithmetic against the official CU course-specification form — the form gate (F.1), every form field, the assessment weights and sub-part splits, the grading table and the policy statements. Loaded by course-reviewer.
---

# Course QA Checklist — method

Sources of truth: `${CLAUDE_PLUGIN_ROOT}/references/checklist.md` (the rules,
their severities, their owners and the precedence list) and
`${CLAUDE_PLUGIN_ROOT}/references/course-spec-template.md` (the form's fields
in order). Read both first. This skill is the method for applying them.

## Method

1. **Read the whole document.** Markdown: read it in full. PDF: read every
   page with the Read tool. If the extracted Thai text looks garbled
   (vowels or tone marks out of place, digits turned into symbols — the real
   `total-cases/2110555.pdf` does this), read the page images instead of the
   text; quote what the page shows.
2. **Form gate first (F.1).** Locate the three parts `course-spec-template.md`
   lists under "Where the form gate looks": the CLO table with a related-PLO
   column, the assessment table with measurement-level and related-CLO
   columns, and the grading section with grade thresholds. If any is
   missing, write exactly one finding under F.1 naming each missing part,
   and stop: check no other rule. Older numbered syllabi and instructor
   handouts fail here. A list of weights under a "Grading" heading is not a
   grading section; the gate needs grade thresholds.
3. **Extract verbatim**, with a line number (Markdown) or page number (PDF):
   the course-information fields, the instructors, the related-PLO list, the
   CLO table, the content table, the assessment table and its note, the
   grading tables, and the remaining sections. Everything after this step is
   checked against the extraction, so do not paraphrase.
4. **Check every rule whose Owner is `course-reviewer`**, in table order,
   applying the precedence list in `checklist.md`. Rules owned by
   curriculum-auditor (2.2, 2.5-2.7, 4.7-4.9) are not yours: do not judge
   Bloom levels, CLO wording or PLO validity. 4.6 is "no level stated", never
   "wrong level".
5. **Do the arithmetic yourself** and state it in the finding or your notes:
   add the assessment-table weights and give the sum and its difference from
   100 ("sum = 95, short by 5"). A component labelled "bonus" is outside the
   sum; name it. For every component the document splits into sub-parts,
   add the sub-parts, compare them with the component's weight and with
   every other statement of the same split (4.10).
6. **Attendance and participation rows** are exempt from 4.4 (no CLO) and 4.6
   (no level). A stated level on such a row is curriculum-auditor's 4.9.
7. **Policy rules 6.1-6.4 are presence checks.** A statement passes wherever
   it appears (usually the assessment note); do not grade its wording. 6.4
   applies only when attendance is graded or required.
8. **Record each failure as one finding** in the `committee-review-format`
   schema: `checklist_rule`, the severity from `checklist.md` unchanged,
   `source_agent: "course-reviewer"`, a section pointer precise enough to
   find the row ("Assessment table → row 'Final exam'"), the verbatim quote
   (the row as printed, or the `-`, or `"(absent)"` for a missing section),
   a message, and a one-sentence fix an instructor can act on without a
   follow-up question. One finding per failing row or field; a multi-field
   rule (1.5, 1.7) gets one finding naming every missing field.
9. **Write** to `reports/<course_code>/findings.json`, creating the directory
   if needed. If that file already exists before you write your first
   finding, it holds an earlier run's findings: do not append to it. Report
   that it exists and stop, so the user can clear `reports/<course_code>/`
   and run again; otherwise the earlier run's open findings would count in
   this verdict. Once you have created the file it is append-only: add
   entries, never rewrite or delete one. The `validate_findings.py` PreToolUse hook blocks a write that
   changes an existing finding, uses a severity other than the checklist's,
   or cites a rule you do not own.
