# Ground truth for the course-spec-qa evaluation

One file per synthetic course in `courses/`, plus the expected batch PLO rollup below. Each file says what a review that follows the rulebook must report — the verdict, every finding with its rule, severity, owner, location and verbatim quote — and the traps a review must not report. The labels follow the rulebook as written; they do not add what an expert might note beyond it.

Keep `evaluation/` out of reach of the run being scored: run each take from a copy of the plugin without this folder, so no take can read the answers.

## Files

| Course | Title | Case | Verdict | Blocker | Major | Minor |
|---|---|---|---|---|---|---|
| [CPE201](CPE201.md) | Data Structures and Algorithms | Clean: complete form; every stated level is consistent with its CLOs and method type | APPROVE | 0 | 0 | 0 |
| [CPE305](CPE305.md) | Database Systems | Clean: Create and Evaluate CLOs measured by project, report and peer-review deliverables | APPROVE | 0 | 0 | 0 |
| [CPE310](CPE310.md) | Computer Networks | Clean: four CLOs, a to-clause verb classified by synonym | APPROVE | 0 | 0 | 0 |
| [CPE410](CPE410.md) | Operating Systems | APPROVE with Minor findings only: three form sections left as - | APPROVE | 0 | 0 | 3 |
| [CPE420](CPE420.md) | Software Engineering Practice | Clean: professional-practice verbs and nouns spelled like dictionary verbs | APPROVE | 0 | 0 | 0 |
| [CPE430](CPE430.md) | Agentic AI Systems | REVISE: PLO list inconsistency, an unassessed CLO, a sub-part split that disagrees | REVISE | 0 | 3 | 0 |
| [CPE440](CPE440.md) | Machine Learning Operations | RETURN: not on the official form | RETURN | 1 | 0 | 0 |
| [CPE450](CPE450.md) | Physics Simulation for Games | RETURN: not on the official form | RETURN | 1 | 0 | 0 |
| [CPE501](CPE501.md) | Machine Learning Fundamentals | REVISE: three assessment-alignment defects | REVISE | 0 | 3 | 0 |
| [CPE502](CPE502.md) | Computer Graphics | RETURN: assessment weights sum to 95; kept for the README hook demo | RETURN | 1 | 0 | 0 |
| [CPE503](CPE503.md) | Game Programming | RETURN: no PLO mapping anywhere, a teaching-aim CLO, blank levels, most sections `-` | RETURN | 4 | 4 | 13 |

Verdicts: 5 APPROVE, 2 REVISE, 4 RETURN.

## Result vocabulary (checklist results tables)

| Result | Meaning |
|---|---|
| PASS | The rule was checked and holds |
| FAIL | The rule was checked and fails; every FAIL has at least one expected finding |
| N/A | The rule's condition does not arise (e.g. 4.10 when nothing is split) |
| SKIPPED | The precedence list in `references/checklist.md` skips the rule; the note names the item |
| NOT CHECKED | F.1 failed, so no other rule is checked |

## Scoring a take

Compare the take's `reports/<code>/findings.json` and `REVIEW_NOTE.md` with each file:

1. **Verdict**: exact match with the expected verdict.
2. **Hits and misses**: a reported finding matches an expected finding when it names the same course, the same location (the CLO row, the assessment row or the section) and the same defect. Each expected finding is a hit if at least one reported finding matches it, and a miss otherwise. A reported finding that names several rows matches the expected finding for each row it names.
3. **Rule and severity accuracy**: for each hit, whether the reported `checklist_rule` and `severity` equal the expected ones.
4. **Duplicates**: further reported findings matching an expected finding that is already hit are duplicates, not false positives.
5. **Tolerated findings**: a reported finding matching a tolerated entry counts neither way.
6. **False positives**: every other reported finding. A match with a must-not-flag entry is a false positive that the entry names; a finding with no checklist rule behind it (for example a missing TQF domain tag, which the checklist does not check yet) is a false positive too.
7. **False-blocker rate**: open blockers reported on the five APPROVE courses.
8. **Weight integrity**: the weight sum a take reports against the "Assessment weights" line of each file.

## Expected batch PLO rollup (`/review-spec --all`)

Courses whose `findings.json` has an open blocker count as claims only (`plo-mapping-standard`).

| PLO | WA attribute | Courses with no open blocker | Courses with an open blocker | Status |
|---|---|---|---|---|
| PLO1 | WA1 Engineering Knowledge | CPE201, CPE305, CPE310, CPE410, CPE501 | CPE502 | covered |
| PLO2 | WA2 Problem Analysis | CPE201, CPE310, CPE410 | — | covered |
| PLO3 | WA3 Design/development of solutions | CPE201, CPE305, CPE410, CPE420, CPE430 | CPE502 | covered |
| PLO4 | WA4 Investigation | CPE305, CPE501 | — | covered |
| PLO5 | WA5 Tool Usage | CPE310, CPE430, CPE501 | — | covered |
| PLO6 | WA6 The Engineer and the World | — | — | gap |
| PLO7 | WA7 Ethics | — | CPE502 | claimed, not yet approved |
| PLO8 | WA8 Individual and Collaborative Team work | CPE420, CPE430 | — | covered |
| PLO9 | WA9 Communication | CPE420, CPE430 | — | covered |
| PLO10 | WA10 Project Management and Finance | CPE420 | — | covered |
| PLO11 | WA11 Lifelong learning | — | — | gap |

## Rulebook version the labels were made against

If a hash below no longer matches, re-check the labels that depend on that file before scoring. Recompute with `Get-FileHash -Algorithm SHA256 <file>` (PowerShell) or `sha256sum <file>`.

| File | sha256 |
|---|---|
| `references/checklist.md` | `f02989d96f5078a1cb3060e41a3ef0dec8291a9c09b66fcb11f15fc4294fc1b8` |
| `references/bloom-taxonomy.md` | `4a0853faaa740ebe042056a31cd0e32808979abf04f01809a1596cba870d51fc` |
| `references/plo-catalog.md` | `f25c1ec835ecb903f88fb3e6cc46244ed0e7d70109b733d968b673e77b32f34d` |
| `references/course-spec-template.md` | `7ee3c4776e49b3b9dc7ee014ef1779ff8f17477da52f66da8b2b0198283be2aa` |
| `skills/course-qa-checklist/SKILL.md` | `df403d54626cfb0c55b35670e6c66aee2f473425ea768c2b122d4deb8e1d9a08` |
| `skills/bloom-verb-rules/SKILL.md` | `7842c29ce5ce932e1f04cedc21aef30f810614ce3c86a2e6e46f2296deff7842` |
| `skills/plo-mapping-standard/SKILL.md` | `ef1aab2197087e561982c223713bc3158382f5a162017da355253843dd0842dc` |
| `skills/committee-review-format/SKILL.md` | `80b4f4ddfcc589a72c3f05da29bc1a778546771d37ec9901f66506f70becf2c2` |
| `courses/CPE201.md` | `29345669f9493f85f3dfe5a8eb6274aa22404e944a12c2c87397c58fda3c972a` |
| `courses/CPE305.md` | `cc77af9504f1ffac6b4d04e548406aa4525c036156671abf600110d6844d5cd2` |
| `courses/CPE310.md` | `88540d21324da7a07d6f130b660173a0226db05590accc0af57e4089439e5ccd` |
| `courses/CPE410.md` | `0e28200de29ea6147ce3d9d342049ae21876787fffe6cec67cf0e8b4a3ada0db` |
| `courses/CPE420.md` | `003174b1085b8efa082084ce32b9c2b569f87d7eeacbfed79abf4e6967807a7f` |
| `courses/CPE430.md` | `30deb1c1d643986a4134acc0ddd60faa82829569f1c7a850da65594e7550a27f` |
| `courses/CPE440.md` | `f50f8c4a087bf8eaad01ba656573d9b6a1d8f34846262b4e503b040939fd3a6f` |
| `courses/CPE450.md` | `4bf50455c1d86b4a2f386c2809d710328304cafd1b86095769d2b52d2515d34f` |
| `courses/CPE501.md` | `1f251af0a267e306c07baf032a611f67644955f0bee34586b8de0977326f9ade` |
| `courses/CPE502.md` | `901ec7173b0eb3cd8932e5965f376c271cac5031cf919ec96358f1f96704415d` |
| `courses/CPE503.md` | `443071c249f63d3e990287ac44787dd8caf247e43c344d57f3d5a29c1047a6f3` |
