# Course Specification QA Plugin

A Claude Code plugin that reviews engineering course specifications for
program QA in Thailand. It checks a specification on the official
Chulalongkorn University course-specification form (ประมวลรายวิชา) against a
fixed rulebook — form completeness, CLO-to-PLO mapping against the program's
PLO catalog, Bloom-level alignment between CLOs and assessment methods,
assessment weights and grading — and writes committee-ready review notes
with a deterministic APPROVE / REVISE / RETURN verdict.

The standards behind the rulebook (TABEE and the Washington Accord graduate
attributes, GAPC 2021.1; Thailand's 2022 higher-education qualification
standards) are summarised with sources in
[`references/tabee-standard.md`](references/tabee-standard.md).

## What it checks

`references/checklist.md` holds 41 rules, one row each, with one severity
and one owning agent per rule (10 Blocker, 11 Major, 20 Minor):

- **Form gate (F.1).** The document must be on the official form: its CLO
  table with a related-PLO column, its assessment table with
  measurement-level and related-CLO columns, and its grading section with
  grade thresholds. A document that is not (an older numbered syllabus, an
  instructor handout) gets one Blocker naming what is missing, and nothing
  else is checked.
- **Course information (1.x)**, **learning outcomes and PLOs (2.x)**,
  **content and teaching (3.x)**, **assessment (4.x)**, **grading (5.x)**,
  **policies (6.x)** and **resources and quality (7.x)**.
- **Bloom levels sit on assessment methods**, as on the real form. Each
  CLO's level is derived from its verbs (`references/bloom-taxonomy.md`);
  rules 4.7-4.9 check that no method claims more than its CLOs ask for,
  that every CLO is measured at its own level, and that the method type can
  evidence the level stated (attendance cannot; an exam cannot show
  Evaluate or Create).
- **Policy statements (6.x) are Minor presence checks**, because the form
  has no policy field.
- A precedence list makes sure each defect is reported once, under one rule.

The verdict is a lookup: any open Blocker → RETURN; else any open Major →
REVISE; else APPROVE.

## Layout

```
.claude-plugin/plugin.json      plugin manifest
commands/review-spec.md         /review-spec <file.md|file.pdf> | --all [directory]
agents/                         course-reviewer -> curriculum-auditor -> verdict-writer
skills/                         course-qa-checklist, bloom-verb-rules,
                                plo-mapping-standard, committee-review-format
hooks/                          block_approve_with_blocker.py (PreToolUse)
                                validate_findings.py (PreToolUse)
                                log_verdict.py (PostToolUse)
hooks/tests/                    unittest suite for the hooks
references/                     checklist.md (the rules), course-spec-template.md (the form),
                                bloom-taxonomy.md, plo-catalog.md (PLACEHOLDER - replace
                                with the program's real PLO catalog before real use),
                                tabee-standard.md (sourced standards summary)
courses/                        11 synthetic specs: 9 on the form in English, 2 off-form
evaluation/                     ground truth, one Markdown file per course + README
total-cases/                    6 real Chulalongkorn syllabi (PDF), the format reference
                                for the corpus and a generalization set
docs/superpowers/               design spec and implementation plan for this revision
reports/                        generated output (COURSE_SPEC_REVIEW.md, per-course
                                REVIEW_NOTE.md and findings.json, PROGRAM_PLO_COVERAGE.md,
                                amendments-queue.csv, audit-log.jsonl)
```

## Try it locally

The hooks are Python and `hooks/hooks.json` invokes them as `python`. On a
machine where only `python3` is on PATH, change the interpreter there — a
missing interpreter exits 127, which Claude Code treats as a non-blocking
error, so the write proceeds and blocker enforcement disappears with no
visible failure.

```
claude --plugin-dir .
```

then, inside the session:

```
/review-spec courses/CPE201.md
/review-spec --all
/review-spec total-cases/2110651.pdf
/review-spec --all total-cases
```

Each run writes `reports/<course_code>/findings.json`, and the hooks forbid
removing a finding from it. Before reviewing a course again, clear
`reports/<course_code>/` (or all of `reports/`, keeping `.gitkeep`); the
reviewer stops rather than mix an earlier run's findings into a new
verdict.

Run the hook tests with:

```
python -m unittest discover -s hooks/tests -v
```

## The hooks

| Hook | When | What it enforces |
|---|---|---|
| `block_approve_with_blocker.py` | Before a Write or Edit of `REVIEW_NOTE.md` or `COURSE_SPEC_REVIEW.md` | No `**Verdict:** APPROVE` while `findings.json` has an open blocker |
| `validate_findings.py` | Before a Write or Edit of any `findings.json` | Every finding cites a checklist rule, uses that rule's severity, comes from the rule's owning agent, and has all required fields; a resolved finding has a `resolution_note`; no existing finding is removed or rewritten |
| `log_verdict.py` | After a `REVIEW_NOTE.md` is written | Appends the verdict, open-finding counts and the sha256 of `checklist.md` to `reports/audit-log.jsonl` |

Skills and agents can be argued out of an instruction; the hooks read only
the files, so they hold whatever reasoning produced the write.

## The corpus and its ground truth

`courses/` is modelled on the real syllabi in `total-cases/`:

| Course | Modelled on | Expected verdict |
|---|---|---|
| CPE201, CPE305, CPE310, CPE420 | The official form (2110651 layout) | APPROVE, no findings |
| CPE410 | 2110743 (a bonus on top of 100) | APPROVE with three Minor findings |
| CPE501 | 2110651 (attendance given a level, an exam claiming Evaluate) | REVISE |
| CPE430 | 2110576 (a final-project split stated two ways) | REVISE |
| CPE502 | 2110514 topics; weights sum to 95 | RETURN |
| CPE503 | 2110511 (teaching-aim CLOs, `-` PLOs, blank levels) | RETURN |
| CPE440 | 2110555 (older numbered form) | RETURN (form gate) |
| CPE450 | 2110514 (one-page handout) | RETURN (form gate) |

Instructor names in `courses/` are fictional placeholders. The clean
courses carry deliberate traps (nouns spelled like Bloom verbs, verbs
classified by synonym or by convention, a bonus outside the 100), so a
reviewer that over-reports is caught.

`evaluation/` holds the ground truth: for each course the expected verdict,
every expected finding with its rule, severity, owner, line and verbatim
quote, all 41 checklist results, tolerated findings, and the traps a review
must not report; `evaluation/README.md` adds the scoring rules, the expected
batch PLO rollup, and the sha256 of every rule file the labels were made
against.

## Experiment design (Take 0 -> Take 4)

Run the same review task through five configurations, same wording each
time, and record what changes:

| Take | Adds | What it should change |
|---|---|---|
| 0 (baseline) | Plain prompt, two fresh sessions, no plugin | Two sensible-but-different answers -- instability is the result being measured |
| 1 | + Skills | More consistent checklist coverage, but verdicts can still drift |
| 2 | + Command | Consistent pipeline invocation, less prompt-wording sensitivity |
| 3 | + Agents | Role separation catches more (Bloom/PLO domain checks appear), findings get citations |
| 4 | + Hooks | Verdict consistency approaches 100% on the Approve/blocker boundary, and findings keep the checklist's severities -- the only layer that holds when a course owner argues in good faith for an Approve despite an open blocker |

Score every take against [`evaluation/`](evaluation/README.md): verdict
accuracy and consistency, hits and misses per expected finding, rule and
severity accuracy, duplicates, false positives (including must-not-flag
traps), the false-blocker rate on the five APPROVE courses, weight
integrity, location precision, plus time, agent turns and cost. Run each
take from a copy of the plugin without `evaluation/`, so no take can read
the answers.

Required evidence for the report: one success case (CPE201 sailing to
APPROVE with no findings), one blocked case (CPE502: prompt the agent,
mid-review, to approve it anyway and watch `block_approve_with_blocker`
deny the write), a baseline-vs-plugin comparison on identical wording, and
a limitations section. The real `total-cases/*.pdf` are good material for
the last one: four of the six are not on the official form, and the two
that are show `-` for every PLO.

## Limitations

- `references/plo-catalog.md` is a placeholder built one-to-one on the
  Washington Accord attributes; a real program's catalog comes from its
  curriculum document and usually has fewer, broader PLOs.
- Some standards claims could not be read from their primary sources during
  research (the TABEE website, the Royal Gazette PDF); `tabee-standard.md`
  marks them unverified.
- Thai text extracted from some PDFs is garbled (vowels and tone marks out
  of place, as in `total-cases/2110555.pdf`); the reviewer is told to read
  such pages as images.
- The synthetic corpus is in English; the Thai verb list in
  `bloom-taxonomy.md` is there for the real Thai PDFs, which have no ground
  truth yet — labelling them needs a qualified human reviewer.
- TQF domain tagging per CLO is not checked: the 2025 form has no such
  field, and domains are carried at program level in the PLO catalog.
