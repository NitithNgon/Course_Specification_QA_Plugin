---
name: plo-mapping-standard
description: Use when validating a course's CLO-to-PLO mappings against the program's PLO catalog and TABEE/Washington-Accord outcome-mapping requirements, including program-level coverage rollups. Loaded by curriculum-auditor.
---

# PLO Mapping Standard — methodology

Sources of truth: `${CLAUDE_PLUGIN_ROOT}/references/plo-catalog.md` (the
program's PLO list) and `${CLAUDE_PLUGIN_ROOT}/references/tabee-standard.md`
(why this matters for accreditation). Read both first.

## Per-course method

1. For every CLO, check its PLO column against `plo-catalog.md`:
   - Empty / `-` with no stated justification → finding, severity
     **Blocker** (this is a Return-tier defect — see the real
     `total-cases/2110511.pdf`, which has this exact defect on all three
     CLOs).
   - Non-empty but the PLO ID does not exist in the catalog → finding,
     severity **Blocker** ("dangling PLO reference").
   - Non-empty and valid → no finding, but record the mapping for the
     rollup step below.
2. Do not judge whether the mapping is a *good* pedagogical fit unless it's
   obviously wrong (e.g. a CLO about attendance mapped to PLO3
   Design/Development) — that's a Minor advisory note, not a blocker; the
   catalog doesn't encode fit, only validity.

## Program-level rollup (only when invoked in `--all` / batch mode)

3. Aggregate CLO→PLO mappings across every course spec processed in this
   run. For each PLO ID in the catalog, count how many courses cover it.
4. Any PLO covered by **zero** courses in the batch is a program-level
   finding (not attached to any single course) — write it to
   `reports/PROGRAM_PLO_COVERAGE.md` as a gap, citing
   `tabee-standard.md`'s note on self-study mapping-matrix requirements.
   This is the artifact a program director uses for TABEE self-study prep.
5. Never fabricate coverage — if a PLO's only coverage comes from a course
   whose own PLO mapping was itself flagged as invalid in step 1, don't
   count it as covered; note it as "coverage claimed but unverified."
