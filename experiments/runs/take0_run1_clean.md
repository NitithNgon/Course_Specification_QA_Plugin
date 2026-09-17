# Take 0 (baseline, no plugin) — Case A (clean, CPE201) — run 1

Condition: fresh general-purpose agent, plain-language QA task, explicitly
barred from Skill/Agent/slash-command tools. Reads only
`courses/clean_01_data_structures.md`.

## Raw report

- [MAJOR] Course Information "skeletal" — missing credit hours, prerequisites,
  term, instructor, description. NOT a real checklist item (checklist 1.1/1.2
  only require course code + name).
- [MINOR] No Textbook/References section, no weekly schedule. Not a real
  checklist item.
- [MINOR] No grading scale. Not a real checklist item.
- PASS: all 3 Bloom verb/level pairs match (Explain/Understand,
  Apply/Apply, Analyze/Analyze) — agrees with gold.
- [MINOR] CLO2->PLO3 mapping "questionable" (Apply-level CLO feeding a
  conventionally Design/Create-level PLO). Judgment call, not in gold.
- [MINOR] CLO1->PLO1 "one Bloom-level below the PLO's usual verb" — judgment
  call, not in gold.
- [MINOR] Document never restates the PLO catalog text — judgment call.
- PASS: CLO-to-assessment coverage complete, no orphans — agrees with gold.
- PASS: weights sum to 100 — agrees with gold (`expected_weight_sum: 100`).
- PASS: policies section is "comparatively strong."

**Verdict: REVISE**

## Scoring vs. courses/gold-labels.json (clean_01, expected_verdict: APPROVE)

Verdict mismatch: REVISE vs gold APPROVE. Every reason cited for REVISE
traces to a hallucinated mandatory field (credit hours, prerequisites, term,
instructor, description, textbooks, weekly schedule, grading scale) that is
not part of this institution's actual `checklist.md` — the baseline is
applying generic curriculum-template conventions instead of the institution's
specific 2-field Course Information requirement. Bloom/PLO/weight substance
checks were all correct in isolation; the false positives are entirely
structural-checklist hallucination.
