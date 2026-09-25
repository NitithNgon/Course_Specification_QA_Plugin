---
name: plo-mapping-standard
description: Use when validating a course's PLO references against the program's PLO catalog (checklist rules 2.5-2.7) and producing the batch PLO coverage rollup for TABEE self-study. Loaded by curriculum-auditor.
---

# PLO Mapping Standard — method

Sources of truth: `${CLAUDE_PLUGIN_ROOT}/references/plo-catalog.md` (the
program's PLO list) and `${CLAUDE_PLUGIN_ROOT}/references/tabee-standard.md`
(why the mapping matters for accreditation). Read both first.

## Per course

1. **Presence is not yours.** Rules 2.3 (related-PLO section) and 2.4 (PLO on
   every CLO) belong to course-reviewer. Never re-report a `-` or a blank
   PLO cell; the precedence list in `checklist.md` makes a `-` 2.3/2.4 only.
2. **2.5 (Blocker):** every PLO ID in the related-PLO section and on every
   CLO must be a `PLO ID` in `plo-catalog.md`. One finding per invalid ID
   and location; `standard_ref`: `"plo-catalog.md: PLO ID '<id>' does not
   exist"`.
3. **2.6 (Major), only when 2.3 and 2.4 passed:** the set of IDs on the CLOs
   must equal the set in the related-PLO section. One finding per ID that is
   in one set and missing from the other, located at the section where it
   is missing, quoting the row or line where the ID does appear.
4. **2.7 (Minor, advisory):** only when a mapping is obviously wrong, e.g. a
   CLO about attendance mapped to a design PLO. Say why the fit is wrong.
   The catalog encodes validity, not fit, so this is never a Blocker or
   Major.

## Batch rollup (`/review-spec --all`)

5. For every PLO in the catalog, list the courses that map at least one CLO
   to it with a valid ID.
6. Split those courses by whether their `findings.json` has an open blocker.
   Coverage from a course with an open blocker is claimed, not approved: the
   spec is going back to its instructor.
7. Write `reports/PROGRAM_PLO_COVERAGE.md`:

```markdown
# Program PLO Coverage — <run date>

| PLO | WA attribute | Courses with no open blocker | Courses with an open blocker | Status |
|---|---|---|---|---|
| PLO1 | WA1 Engineering Knowledge | CPE101, CPE102 | CPE103 | covered |
| PLO4 | WA4 Investigation | — | — | gap |
| PLO8 | WA8 Individual and Collaborative Team work | — | CPE103 | claimed, not yet approved |
```

   Status is `covered` when the third column names a course, `claimed, not
   yet approved` when only the fourth does, and `gap` when neither does.
   Under the table, list the gaps and cite `tabee-standard.md`: a PLO no
   course covers is a gap in the course-to-PLO mapping a TABEE self-study
   relies on.
