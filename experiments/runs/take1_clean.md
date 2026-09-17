# Take 1 (+Skill, single agent) — Case A (clean, CPE201)

Condition: fresh agent, explicitly told to load and apply
course-qa-checklist / bloom-verb-rules / plo-mapping-standard /
committee-review-format via the Skill tool itself; no subagent delegation,
no slash command; no file writes.

## Result

Full 19-item checklist walkthrough against the real `checklist.md`, all
PASS. Bloom verb/level table: all 3 exact dictionary matches. PLO table: all
3 valid, no dangling references, no obviously-wrong fit flagged.
Weight sum: 100, delta 0.

**Findings: 0 blocker / 0 major / 0 minor.**
**Verdict: APPROVE** (via the real policy table: no blocker -> not RETURN,
no major -> not REVISE -> APPROVE).

## Scoring vs. gold (expected_verdict: APPROVE)

Exact match: verdict correct, weight sum correct, 0 false positives.
This is the first condition in the matrix to land exactly on gold with zero
noise for this case.
