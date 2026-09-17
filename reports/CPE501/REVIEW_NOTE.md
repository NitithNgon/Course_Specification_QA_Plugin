# Review Note — CPE501: Machine Learning Fundamentals

**Verdict:** REVISE

## Findings

### [MAJOR] 3.6 — Section 2 -> Learning Outcomes table -> row 'CLO2'; Section 3 -> Assessment table -> row 'Midterm Exam (closed book)'
> CLO2 | Define the standard supervised learning model families (linear, tree-based, neural) | Create | PLO3 -- mapped only by: Midterm Exam (closed book) | 30 | CLO1, CLO2

CLO2's stated Bloom level is Create, but the only assessment component mapped to CLO2 is the Midterm Exam (closed book), which is exam-only; no project/design/critique deliverable is mapped to CLO2 (the Project row is mapped only to CLO1, CLO3).

**Fix:** Add CLO2 to the CLO-Mapped column of the Project row (or another project/design/critique component) so a stated Create-level outcome is assessed by more than a closed-book exam.

### [MAJOR] 2.4 — Section 2 -> Learning Outcomes table -> row 'CLO2'
> CLO2 | Define the standard supervised learning model families (linear, tree-based, neural) | Create | PLO3

CLO2's driving verb is 'Define,' which is a literal dictionary match for the Remember level (level 1 of 6) — the lowest cognitive level in Bloom's taxonomy. The CLO's stated Bloom level is Create (level 6), the highest level. This is a 5-level over-claim, the most extreme possible mismatch between stated level and verb-implied level. Per bloom-verb-rules, a stated level higher than the verb supports is a finding regardless of any downstream assessment analysis. Note for the committee: this verb-level correction also reframes the related major finding on checklist 3.6 — if CLO2's true cognitive demand is Remember (not Create), the Midterm Exam mapping is actually congruent evidence per the bloom-taxonomy.md congruence table (MCQ/short-answer exam evidences Remember/Understand); the defect is the mislabeled Bloom level itself, not necessarily the assessment choice. This does not change the severity or status of that finding — that determination is keyed off the stated (not corrected) level.

**Fix:** Either (a) reword CLO2 with a verb that genuinely supports Create-level demand (e.g., 'Design and construct a supervised learning pipeline that selects among model families...') and ensure at least one project/design deliverable is mapped to it, or (b) correct the stated Bloom level to Remember (or a verb/level that matches the intended cognitive demand, e.g. 'Compare' for Analyze) and confirm the exam-based assessment mapping is adequate at that corrected level.

### [MINOR] PLO mapping judgment call — Section 2 -> Learning Outcomes table -> row 'CLO2'
> CLO2 | Define the standard supervised learning model families (linear, tree-based, neural) | Create | PLO3

PLO3 is a valid PLO ID (exists in plo-catalog.md), so this is not a blocker/dangling-reference defect. However, the mapping looks like a poor pedagogical fit: CLO2's actual verb ('define') describes a knowledge-recall outcome — enumerating/defining supervised learning model families — with no design, construction, or system-development activity involved. PLO3 specifically concerns designing software/hardware systems that meet specified requirements, which CLO2 as written does not exercise. PLO1 ('Apply mathematics, science, and computer engineering fundamentals...') is a closer fit for a definitional/knowledge-level CLO.

**Fix:** Consider remapping CLO2 to PLO1 unless the course intends CLO2 to culminate in an actual design task, in which case the verb, stated Bloom level, and assessment mapping (see the checklist-3.6 finding above) should all be revised together to genuinely support Create-level, PLO3-appropriate evidence.

## Standards cited
- Bloom's Taxonomy (Anderson & Krathwohl, 2001): verb 'define' = Remember (literal dictionary match — 'define' is listed under the Remember level in bloom-taxonomy.md), but CLO2 states Create.
- plo-catalog.md: PLO3 = 'Design software/hardware systems and components that meet specified requirements' (PLO ID is valid, not a dangling reference); plo-mapping-standard skill: pedagogical-fit judgment call (advisory, Minor per skill instructions).
