# Course QA Checklist

These rules apply to a course specification on the official Chulalongkorn
University course-specification form (ประมวลรายวิชา). The form's fields, in
order, are listed in `course-spec-template.md`; the synthetic specs in
`courses/` use its English rendering, and real specs arrive as Thai PDFs.

Every row below is one rule with one severity and one owning agent. A rule
that fails becomes one finding with a location, a verbatim quote and a
one-sentence fix (see the `committee-review-format` skill).

`hooks/validate_findings.py` reads this table before any `findings.json`
write lands: it blocks a finding whose rule is not a row here, whose
severity differs from the row's severity, or whose source agent is not the
row's owner. Keep the column order `ID | Check | Severity | Owner` and one
rule per row. Changing a severity here changes it for every agent and for
the hook at once; no agent may use a different severity.

## Rules

| ID | Check | Severity | Owner |
|---|---|---|---|
| F.1 | The document is on the official course-specification form: its CLO table (with a related-PLO column), its assessment table (with measurement-level and related-CLO columns) and its grading section with grade thresholds can all be located. If any is missing, report F.1 once, naming each missing part, and check no other rule | Blocker | course-reviewer |
| 1.1 | Course code is present and matches the file name | Blocker | course-reviewer |
| 1.2 | Course title is present in at least one language | Blocker | course-reviewer |
| 1.3 | Course title is present in both Thai and English | Minor | course-reviewer |
| 1.4 | Credits are stated in the form N (L-P-S), e.g. 3 (3-0-6) | Minor | course-reviewer |
| 1.5 | Faculty, department, semester and academic year are stated | Minor | course-reviewer |
| 1.6 | A course coordinator and at least one instructor are named | Minor | course-reviewer |
| 1.7 | Degree level, related curricula, course status and course description are stated | Minor | course-reviewer |
| 2.1 | At least one CLO is listed | Blocker | course-reviewer |
| 2.2 | Every CLO has at least one verb that names something the student does and can be classified with `bloom-taxonomy.md`; a CLO with none, i.e. a teaching aim such as "Give students a foundation in ...", fails | Major | curriculum-auditor |
| 2.3 | The related-PLO section lists at least one PLO ID; `-` or blank fails | Blocker | course-reviewer |
| 2.4 | Every CLO maps to at least one PLO ID; `-` or blank without a stated reason fails | Blocker | course-reviewer |
| 2.5 | Every PLO ID cited, in the related-PLO section or on a CLO, exists in `plo-catalog.md` | Blocker | curriculum-auditor |
| 2.6 | The set of PLO IDs on the CLOs equals the set in the related-PLO section | Major | curriculum-auditor |
| 2.7 | Advisory: a CLO-to-PLO mapping is an obvious poor fit; the finding says why | Minor | curriculum-auditor |
| 3.1 | Content topics are listed | Minor | course-reviewer |
| 3.2 | Every CLO is covered by at least one content topic | Minor | course-reviewer |
| 3.3 | Teaching media are stated | Minor | course-reviewer |
| 3.4 | A communication channel or LMS is stated | Minor | course-reviewer |
| 4.1 | At least one assessment method is listed with a weight | Blocker | course-reviewer |
| 4.2 | Every weight is a non-negative number | Blocker | course-reviewer |
| 4.3 | The weights in the assessment table sum to exactly 100; a component labelled "bonus" is outside the sum | Blocker | course-reviewer |
| 4.4 | Every assessment method except attendance or participation maps to at least one CLO | Major | course-reviewer |
| 4.5 | Every CLO is assessed by at least one method | Major | course-reviewer |
| 4.6 | Every assessment method except attendance or participation states a measurement level | Major | course-reviewer |
| 4.7 | No method's measurement level is higher than the highest derived level among the CLOs it assesses | Major | curriculum-auditor |
| 4.8 | Every CLO is assessed at its derived level or higher by at least one method | Major | curriculum-auditor |
| 4.9 | Every method's measurement level is one its method type can evidence (`bloom-taxonomy.md`, "Method types"): an attendance or participation row that states a level fails, and Evaluate or Create needs a project, design, report, presentation, critique or peer-review deliverable | Major | curriculum-auditor |
| 4.10 | Where a method is split into sub-parts, the sub-parts sum to its weight and every statement of the split agrees | Major | course-reviewer |
| 5.1 | A threshold is listed for every grade from A to D, with F as the remainder | Major | course-reviewer |
| 5.2 | Thresholds fall strictly from A to D and lie between 0 and 100 | Major | course-reviewer |
| 6.1 | A deadline or late-submission policy is stated | Minor | course-reviewer |
| 6.2 | An academic-integrity and plagiarism statement is present | Minor | course-reviewer |
| 6.3 | A statement on the use of AI tools is present | Minor | course-reviewer |
| 6.4 | An attendance policy is stated when attendance is graded or required | Minor | course-reviewer |
| 7.1 | A reading list is given | Minor | course-reviewer |
| 7.2 | A teaching-evaluation channel is stated | Minor | course-reviewer |
| 7.3 | Changes made after the previous teaching evaluation are stated ("first offering" passes; `-` fails) | Minor | course-reviewer |
| 7.4 | The response to student complaints is stated | Minor | course-reviewer |
| 7.5 | The AI-related learning section is complete: either no AI topics with 0 hours, or topics with hours and both strategies | Minor | course-reviewer |
| 7.6 | SDG alignment is stated | Minor | course-reviewer |

Rules 6.1-6.4 are presence checks: a statement passes when it exists, in
the assessment note or anywhere else in the document; its wording is not
graded. They are Minor because the official form has no policy field.

## Precedence

Each defect is reported once, under one rule.

1. If F.1 fails, no other rule is checked.
2. 2.6 is checked only when 2.3 and 2.4 pass. 3.2 is checked only when 3.1 passes.
3. 4.7 and 4.9 skip a method that fails 4.4 or 4.6. 4.7 uses only CLOs whose
   level can be derived; if none can, it skips the method.
4. 4.7 and 4.8 skip a CLO that fails 2.2 (its level cannot be derived).
5. 4.8 skips a CLO that fails 4.5, and counts only methods that state a
   level; if none of the CLO's methods states a level, 4.8 skips the CLO.
6. A method that fails 4.7 is not also reported under 4.9; its level is
   corrected first and 4.9 is checked again after the fix.
7. A `-` in a PLO cell is 2.3 or 2.4 only, never 2.5.

## Findings granularity

- One finding per failing row (a CLO row or an assessment row) or per
  failing section.
- A rule that covers several fields (1.5, 1.7) produces one finding naming
  every missing field.
- Severity and source agent come from the table above, unchanged.
