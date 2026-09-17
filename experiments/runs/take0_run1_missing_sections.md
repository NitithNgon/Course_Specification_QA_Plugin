# Take 0 (baseline, no plugin) — Case B (missing sections, CPE599) — run 1

Condition: fresh general-purpose agent, plain-language QA task, explicitly
barred from Skill/Agent/slash-command tools. Reads only
`experiments/cases/missing_sections_CPE599.md`.

## Raw report

1. [BLOCKER] Missing Course Description / Objectives section — not part of
   this institution's actual checklist (checklist.md has no such item).
   Hallucinated requirement.
2. [BLOCKER] Missing Course Policies section (attendance / integrity /
   late-submission / grading scale) — genuine match to checklist 4.1-4.5,
   but assigned Blocker where the real severity table says Minor (4.1, 4.2,
   4.5) / Major (4.3, 4.4), never Blocker.
3. [BLOCKER] Missing Course Content / Weekly Schedule section — not part of
   this institution's actual checklist. Hallucinated requirement.
4. [MAJOR] Course Information section skeletal (no credit hours,
   prerequisites, term, instructor) — not part of this institution's actual
   checklist (checklist 1.1/1.2 only require course code + name, both
   present).
5. [MAJOR] Missing Teaching and Learning Methods section — hallucinated
   requirement, not in checklist.md.
6. [MINOR] Missing Textbooks/References section — hallucinated requirement,
   not in checklist.md.
7. [MINOR] CLO3 Bloom-verb borderline Analyze/Evaluate — plausible judgment
   call, not in gold expectation (gold treats CLO1-3 as clean Bloom matches).
8. OK: CLO1/CLO2 Bloom verbs match.
9. MINOR/INFO: PLO mapping plausibility check (no access to real catalog by
   design of this baseline condition) — mappings judged plausible.

Weight sum: 100/100, correctly computed, matches gold (`expected_weight_sum: 100`).

**Verdict: RETURN**

## Scoring vs. experiments/cases/missing_sections_CPE599.gold.json

- Weight sum: correct (100).
- Verdict: **RETURN vs gold-expected REVISE** — mismatch. Severity inflation:
  baseline treated missing-policy-section as Blocker; real checklist caps it
  at Minor/Major, never Blocker, so the real pipeline should land on REVISE
  (major-but-no-blocker), not RETURN.
- Checklist fidelity: 3 of 6 findings (course description, weekly schedule,
  teaching methods / textbooks) reference sections that do not exist in this
  institution's actual `checklist.md` — the baseline substituted generic
  curriculum-review conventions for the institution's specific 4-section
  template, because it has no access to `checklist.md` without the Skill.
- Genuine checklist-4 findings (attendance/deadlines/integrity/plagiarism/
  AI-tools) were caught in substance but not decomposed into the 5 discrete
  checklist items (4.1-4.5) or given the checklist's specific severities.
