# Course Specification QA Plugin

A Claude Code plugin that reviews course specifications against an
institutional checklist, verifies assessment weights and Bloom/PLO mapping
against TABEE / Thai TQF:HEd / Bloom's Revised Taxonomy, and produces
committee-ready review notes with a deterministic Approve/Revise/Return
verdict.

## Layout

```
.claude-plugin/plugin.json   - plugin manifest
commands/review-spec.md      - /review-spec [file | --all]
agents/                      - course-reviewer, curriculum-auditor, verdict-writer
skills/                      - course-qa-checklist, bloom-verb-rules,
                                plo-mapping-standard, committee-review-format
hooks/                       - PreToolUse block-approve-with-blocker,
                                PostToolUse log-verdict
references/                  - checklist.md, bloom-taxonomy.md, tabee-standard.md,
                                plo-catalog.md (TEMPLATE - replace with the real
                                institutional PLO catalog before real use)
courses/                     - 8 synthetic test specs (5 clean + 3 problematic)
                                and gold-labels.json ground truth
reports/                     - generated output (COURSE_SPEC_REVIEW.md,
                                per-course REVIEW_NOTE.md, audit-log.jsonl)
total-cases/                 - 6 REAL course specs (PDF), used as a separate
                                format-robustness / generalization corpus,
                                not the controlled experiment set
reports/amendments-queue.csv - non-Approve findings queued for instructor action
```

## Try it locally

```
claude --plugin-dir .
```
then, inside the session:
```
/review-spec courses/clean_01_data_structures.md
/review-spec --all
```

## Experiment design (Take 0 -> Take 4)

Run the same review task through five configurations, same wording each
time, and record what changes:

| Take | Adds | What it should change |
|---|---|---|
| 0 (baseline) | Plain prompt, two fresh sessions, no plugin | Two sensible-but-different answers -- instability is the result being measured |
| 1 | + Skills | More consistent checklist coverage, but verdicts can still drift |
| 2 | + Command | Consistent pipeline invocation, less prompt-wording sensitivity |
| 3 | + Agents | Role separation catches more (Bloom/PLO domain checks appear), findings get citations |
| 4 | + Hooks | Verdict consistency approaches 100% specifically on the Approve/blocker boundary -- this is the only layer that holds when a course owner argues in good faith for an Approve despite an open blocker |

Score every take against `courses/gold-labels.json` on:
checklist coverage, completeness, weight integrity, Bloom/PLO detection
rate, verdict consistency, plus time/agent-turns/cost, false-blocker rate
on the 5 clean cases, and location-precision of findings.

Required evidence for the report: one success case (a clean spec sailing to
APPROVE with 0 findings), one blocked/failure case (a blocker spec where the
PreToolUse hook actually fires — try prompting the agent, mid-review, to
approve `blocker_02_weight_95.md` anyway and see the hook deny it), a
baseline-vs-plugin comparison on identical wording, and a limitations
section (the real `total-cases/*.pdf` are good material for this — they're
messier than the synthetic set and expose format-completeness gaps the
synthetic corpus doesn't).
