# Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001) — verb dictionary

Six cognitive levels, lowest to highest. A CLO's *stated* Bloom level must
match the cognitive demand of its *actual verb* — this is the single most
common defect in course specs (an instructor writes "Analyze" but the verb
used, and the way it's assessed, is really "Remember").

| Level | Representative verbs | Typical evidence |
|---|---|---|
| 1. Remember | define, list, recall, identify, name, state, label | Recall-based quiz/exam item |
| 2. Understand | explain, summarize, describe, classify, interpret, discuss | Short-answer, paraphrase, concept map |
| 3. Apply | apply, demonstrate, implement, solve, use, execute, calculate | Problem set, lab exercise, coding exercise |
| 4. Analyze | analyze, compare, differentiate, organize, deconstruct, examine | Case analysis, debugging exercise, comparative report |
| 5. Evaluate | evaluate, critique, justify, argue, assess, defend, recommend | Peer review, design critique, justified recommendation |
| 6. Create | design, develop, construct, formulate, produce, plan, compose | Term project, original design/build deliverable |

## Verb → level lookup (used to classify a CLO automatically)

```
remember:  define, list, recall, identify, name, state, label, recognize
understand: explain, summarize, describe, classify, interpret, discuss, translate
apply:     apply, demonstrate, implement, solve, use, execute, calculate, operate
analyze:   analyze, compare, differentiate, organize, deconstruct, examine, distinguish
evaluate:  evaluate, critique, justify, argue, assess, defend, recommend, judge
create:    design, develop, construct, formulate, produce, plan, compose, devise
```

If a CLO's verb doesn't appear here, classify by the closest synonym and
note the classification as inferred, not literal, in the finding.

## Assessment-method congruence

A Bloom level claim is only as good as the assessment method that can
actually produce evidence of it. Flag a mismatch whenever the *highest*
Bloom level claimed for a CLO is not evidenced by at least one congruent
assessment method mapped to that CLO:

| Bloom level | Assessment methods that CAN evidence it | Methods that generally CANNOT alone |
|---|---|---|
| Remember / Understand | MCQ/short-answer exam, quiz, recitation | — |
| Apply | Problem set, lab, coding assignment, in-class exercise | Pure recall MCQ exam |
| Analyze | Case study, comparative analysis, debugging/diagnosis task | Pure recall MCQ exam |
| Evaluate | Critique assignment, peer review, justified design choice write-up | MCQ exam, simple problem set |
| Create | Term project, capstone design, original build/deployment deliverable | MCQ exam, short-answer exam, quiz |

**Rule of thumb used by curriculum-auditor:** a CLO claiming Evaluate or
Create must be mapped to at least one assessment component that is a
project/design/critique deliverable — a midterm/final exam alone is
insufficient evidence, regardless of how the exam questions are phrased,
unless the spec includes actual exam item text showing an evaluate/create-
level task (e.g. an open-ended design question), in which case quote it.
