# TABEE / Washington Accord Outcome Standard (reference summary)

> **Status:** Summary reference for QA purposes, not a verbatim legal reproduction.
> Verify wording against the current official TABEE Manual and Thai TQF:HEd handbook before using this in an actual accreditation submission.

## What TABEE is

TABEE (Thailand Accreditation Board of Engineering Education) accredits Thai
engineering programs. It has been a **Washington Accord** signatory since 2015
(provisional) / 2019 (full signatory), meaning TABEE-accredited degrees are
mutually recognized by other Washington Accord bodies (e.g. ABET-EAC in the
US, Engineers Australia, JABEE in Japan).

Two things matter for course-spec QA:

1. **Program Learning Outcomes (PLOs) must trace to the Washington Accord's
   12 Graduate Attributes.** A course spec's PLO codes are only meaningful if
   they resolve to entries in the program's official PLO catalog, and that
   catalog should in turn be traceable to these attributes.
2. **Curriculum mapping must be explicit and auditable.** TABEE self-study
   documentation requires a course-to-outcome mapping matrix showing which
   courses deliver which PLOs, and at what level (introduced / reinforced /
   mastered). A course spec with an unmapped or invalid PLO reference breaks
   this matrix.

## Washington Accord Graduate Attributes (the 12, used by TABEE)

| # | Attribute | Short gloss |
|---|---|---|
| 1 | Engineering Knowledge | Apply knowledge of math, science, and engineering fundamentals |
| 2 | Problem Analysis | Identify, formulate, and analyze engineering problems |
| 3 | Design/Development of Solutions | Design solutions meeting specified needs, with public health/safety/cultural/environmental considerations |
| 4 | Investigation | Conduct investigations of complex problems using research-based methods |
| 5 | Modern Tool Usage | Select and apply appropriate techniques, resources, and tools |
| 6 | Engineer and Society | Assess societal, health, safety, legal, and cultural issues |
| 7 | Environment and Sustainability | Understand the impact of engineering solutions in a societal/environmental context |
| 8 | Ethics | Apply ethical principles and professional responsibilities |
| 9 | Individual and Teamwork | Function effectively as an individual and in team settings |
| 10 | Communication | Communicate effectively with the engineering community and society |
| 11 | Project Management and Finance | Apply engineering/management principles to manage projects |
| 12 | Life-long Learning | Recognize the need for, and engage in, independent and life-long learning |

Cross-reference: US ABET-EAC's domestic criteria consolidate a similar set
into 7 Student Outcomes (post-2019 revision). When a program targets dual
recognition, PLOs are often phrased to satisfy both mappings simultaneously —
`references/plo-catalog.md` in this plugin uses the 12-attribute numbering
since that is what a Washington Accord signatory like TABEE reports against.

## Thai TQF:HEd (มคอ.3 / TQF3) — the document standard

The Thai Qualifications Framework for Higher Education is the standard that
defines the **course specification document itself** (the "ประมวลรายวิชา" /
TQF3 form your institution uses). It requires CLOs to be tagged against five
Domains of Learning:

1. Ethics and Moral Development
2. Knowledge
3. Cognitive Skills
4. Interpersonal Skills and Responsibility
5. Numerical Analysis, Communication, and Information Technology Skills

A course spec that states Bloom levels but never ties them back to one of
these five domains is TQF3-incomplete even if it is otherwise well written.

## What curriculum-auditor checks against this file

- Every PLO code cited in a course spec resolves to a real row in
  `plo-catalog.md` (no dangling references).
- Every CLO maps to at least one PLO (no "-" placeholders left in production
  specs — see the real 2110511 case in `total-cases/`, which currently has
  exactly this defect).
- Aggregated across a batch of courses (`/review-spec --all`), every PLO in
  the catalog is covered by at least one course — a gap here is a real
  accreditation self-study risk, not just a per-course nitpick.
