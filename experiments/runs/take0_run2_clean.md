# Take 0 (baseline, no plugin) — Case A (clean, CPE201) — run 2

Same condition/constraints as run 1, independent fresh agent.

## Raw report

- [MAJOR] Missing credit hours, prerequisites, description, instructor — not
  a real checklist item.
- [MAJOR] No syllabus/weekly-topics section, no textbooks/references section
  — not a real checklist item.
- [MINOR] PLOs cited but never defined in-document — judgment call, not in
  checklist (PLO catalog is expected to live at program level, not restated
  per-course).
- [MINOR] No grade-appeal / accommodation statement — not a real checklist
  item.
- PASS: all 3 Bloom verb/level pairs match — agrees with gold.
- PASS: CLO->PLO mapping "internally coherent," flagged as unverified
  against real catalog (reasonable caveat, no defect claimed).
- PASS: every CLO evidenced by an assessment component, CLO3 not exam-only.
- PASS: weights sum to 100 — agrees with gold.

**Verdict: REVISE**

## Scoring vs. gold (expected_verdict: APPROVE)

Verdict mismatch: REVISE vs gold APPROVE, same root cause as run 1 —
hallucinated mandatory fields not present in this institution's actual
4-section / 2-field Course Information checklist.

## Take 0 instability summary (run 1 vs run 2, same case, same wording)

Both runs converged on the same top-line verdict (REVISE) — NOT the
"different verdicts" pattern the experiment plan anticipated. Instability
instead shows up one level down: the two runs cite different specific
missing-field sets (run 1: credit hours/prerequisites/term/instructor/
description + a CLO2->PLO3 fit critique; run 2: credit hours/prerequisites/
description/instructor + syllabus/textbooks + "PLOs undefined in-document")
and different severities for overlapping complaints. Both are wrong relative
to gold for the same underlying reason: absent the institution's actual
checklist.md, a competent generalist reviewer substitutes generic
curriculum-template conventions, and those conventions are close enough
between runs to agree on "needs work" but not on which fields matter, so the
top-line verdict is coincidentally stable while the substantive finding list
is not.
