---
name: bloom-verb-rules
description: Use when deriving each CLO's cognitive level from its verbs and checking each assessment method's stated measurement level against its CLOs and its method type, per Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001). Covers checklist rules 2.2, 4.7, 4.8 and 4.9. Loaded by curriculum-auditor.
---

# Bloom Verb Rules — method

Source of truth: `${CLAUDE_PLUGIN_ROOT}/references/bloom-taxonomy.md` (the
verb dictionary, the derivation rules, the Thai terms and the method-type
table). The precedence list in `${CLAUDE_PLUGIN_ROOT}/references/checklist.md`
decides what each rule skips. Read both first.

## Method

1. **Derive each CLO's level** ("Deriving a CLO's level" in
   `bloom-taxonomy.md`): classify every verb that names something the
   student does, including a verb in a "to ..." clause, and take the highest
   level. Nouns and verbs whose subject is not the student are not
   classified. Record each verb and its level in your notes.
2. **Synonyms and professional-practice verbs** are classified and named in
   your notes ("'build' classified as Create by analogy to 'construct'";
   "'function' is Apply by convention"). They are never findings.
3. **Rule 2.2:** a CLO with no classifiable student verb fails 2.2 (Major).
   Its level stays unknown, so 4.7 and 4.8 skip it. A CLO worded as an aim
   that still contains classifiable student verbs passes 2.2.
4. **Per assessment method** that states a level and maps to at least one
   CLO (methods failing 4.4 or 4.6 are course-reviewer's findings; skip
   them):
   - **4.7:** the stated level must not be higher than the highest derived
     level among its mapped CLOs. Ignore CLOs whose level is unknown; if all
     are unknown, skip the method.
   - **4.9**, only when 4.7 passed: the method's type must be able to
     evidence the stated level (the "Method types" table). An attendance or
     participation row that states any level fails 4.9.
5. **Per CLO** with a derived level and at least one mapped method that
   states a level — **4.8:** at least one of those methods states the CLO's
   level or higher. Skip a CLO no method assesses (that is 4.5).
6. **Cite the standard in every finding's `standard_ref`**, e.g.
   `"Bloom's Taxonomy (Anderson & Krathwohl, 2001): 'define' = Remember;
   method 'Final exam' stated at Evaluate"`. For `function` and
   `communicate`, say the level is assigned by convention, not by the
   taxonomy.
7. **Append** each finding to `reports/<course_code>/findings.json` with
   `source_agent: "curriculum-auditor"` and the severity from
   `checklist.md`. Never rewrite course-reviewer's entries; the
   `validate_findings.py` hook blocks it.
