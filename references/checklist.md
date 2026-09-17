# Course QA Checklist

Every item below is applicable to every course spec unless marked optional.
`course-reviewer` walks this list top to bottom; every FAIL becomes a finding
with a section pointer, a verbatim quote of what's actually there, and a
suggested fix. Items are grouped to match the `course_specification.md`
template's four sections.

## 1. Course Information
- [ ] 1.1 Course code is present and matches the filename/registration code
- [ ] 1.2 Course name is present

## 2. Learning Outcomes
- [ ] 2.1 At least one CLO is listed
- [ ] 2.2 Every CLO has a non-empty description
- [ ] 2.3 Every CLO states a Bloom level (one of: Remember, Understand,
      Apply, Analyze, Evaluate, Create)
- [ ] 2.4 Every CLO's stated Bloom level matches the cognitive level implied
      by its actual verb (see `bloom-verb-rules` skill / `bloom-taxonomy.md`)
- [ ] 2.5 Every CLO maps to at least one PLO ID
- [ ] 2.6 Every PLO ID cited exists in `plo-catalog.md` (no dangling
      references)

## 3. Assessment
- [ ] 3.1 At least one assessment component is listed with a weight
- [ ] 3.2 Every assessment component's weight is a non-negative number
- [ ] 3.3 Weights sum to 100 (± tolerance, default tolerance = 0; a program
      may configure a rounding tolerance, but the default assumes exact)
- [ ] 3.4 Every assessment component maps to at least one CLO
- [ ] 3.5 A scoring criteria / rubric section is present (even a checklist
      of criteria counts; a bare weight with no rubric does not)
- [ ] 3.6 For every CLO whose highest stated Bloom level is Evaluate or
      Create, at least one mapped assessment component is a
      project/design/critique deliverable, not exam-only (see
      `bloom-taxonomy.md` congruence table)

## 4. Course Policies
- [ ] 4.1 Attendance policy stated
- [ ] 4.2 Deadline / late-submission policy stated
- [ ] 4.3 Academic integrity statement present
- [ ] 4.4 Plagiarism and false-citation statement present
- [ ] 4.5 AI Tools & Critical Use statement present (mandatory in current
      template revision — courses reviewed against an older template
      revision without this section should be flagged as
      template-migration-pending, not silently passed)

## Severity defaults (overridable by verdict-writer's policy table)
- **Blocker:** 1.1, 1.2, 2.1, 2.2, 2.5, 2.6, 3.1–3.3
- **Major:** 2.3, 2.4, 3.4, 3.6, 4.3, 4.4
- **Minor/Advisory:** 3.5, 4.1, 4.2, 4.5
