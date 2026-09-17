---
name: bloom-verb-rules
description: Use when classifying a CLO's true cognitive level from its action verb, and checking whether the CLO's assessment method can actually evidence that level, per Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001). Loaded by curriculum-auditor.
---

# Bloom Verb Rules — methodology

Source of truth: `${CLAUDE_PLUGIN_ROOT}/references/bloom-taxonomy.md`. Read
that file first for the verb dictionary and the assessment-congruence table.

## Method

1. For each CLO, extract the main verb(s) driving the outcome (a CLO
   sometimes chains verbs, e.g. "design, develop, and evaluate" — classify
   at the *highest* level among them; a curriculum-auditor's job is to catch
   inflated claims, not deflate honest ones).
2. Look the verb up in the dictionary. If it's a close synonym rather than
   an exact match, say so in the finding ("classified 'craft' as
   Create-level by analogy to 'construct'").
3. Compare the derived level against the CLO's *stated* Bloom level in the
   spec.
   - Match → no finding.
   - Stated level is **higher** than the verb supports (e.g. stated
     "Analyze" but verb is "define") → finding, severity Major, cite the
     specific verb and the dictionary entry.
   - Stated level is **lower** than the verb supports → still a finding
     (Minor) — under-claiming still breaks the curriculum's outcome-mapping
     accuracy, even though it's less committee-critical than over-claiming.
4. Independently of the label mismatch, check assessment congruence: for
   every CLO whose *effective* (verb-derived) level is Evaluate or Create,
   confirm at least one of its mapped assessment components is a
   project/design/critique deliverable per the congruence table. An exam-
   only mapping at these levels is a finding regardless of whether the
   stated Bloom level matched the verb.
5. Every finding must cite the standard by name: `"Bloom's Taxonomy
   (Anderson & Krathwohl, 2001): verb '<verb>' = <level>"` — this is what
   makes the finding defensible to a committee instead of an opinion.
6. Append findings to `reports/<course_code>/findings.json` using the same
   schema `course-reviewer` used (see `committee-review-format` skill).
   Never overwrite course-reviewer's entries — append only.
