# Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001) — verb dictionary and method types

Six cognitive levels, lowest to highest:
Remember < Understand < Apply < Analyze < Evaluate < Create.

On the official course-specification form the Bloom level is stated on each
**assessment method** (the "Measurement level" column), not on each CLO.
A CLO's level is derived from its verbs with the rules below, and
`checklist.md` rules 4.7-4.9 compare the two.

## Verb → level lookup

This block is the **only** verb list in this file. An earlier revision kept a
second copy inside a level table, the two drifted apart by six verbs, and a
CLO was then classified differently depending on which list the reviewer
happened to read. Do not reintroduce a second copy — if a verb needs adding,
add it here.

```
remember:   define, list, recall, identify, name, state, label, recognize
understand: explain, summarize, describe, classify, interpret, discuss, translate
apply:      apply, demonstrate, implement, solve, use, execute, calculate, operate, conduct
analyze:    analyze, compare, differentiate, organize, deconstruct, examine, distinguish, select
evaluate:   evaluate, critique, justify, argue, assess, defend, recommend, judge
create:     design, develop, construct, formulate, produce, plan, compose, devise
```

`conduct` sits at Apply because the verb denotes carrying out a procedure,
alongside `execute`. `select` sits at Analyze because Anderson & Krathwohl
list *selecting* as a cognitive process under **Differentiating**, which is
in the Analyze category — the same place `differentiate` and `distinguish`
sit.

## Professional-practice verbs

The Washington Accord graduate attributes, and therefore `plo-catalog.md`,
use outcome verbs that Anderson & Krathwohl's cognitive taxonomy does not
classify, because they describe professional behaviour rather than a
cognitive process:

```
apply:  function, communicate
```

These are assigned a level **for QA purposes only**, so the Bloom checks can
run without reporting a false mismatch. Do not cite Anderson & Krathwohl as
the authority for either one; when a finding turns on one of these verbs,
say that the level is assigned by convention.

They are here because course specs are supposed to echo the wording of the
PLO they map to: `function` comes from PLO8 (WA8, "Function effectively as
an individual, and as a member or leader in diverse teams") and
`communicate` from PLO9 (WA9, "Communicate effectively ..."). A CLO that
traces visibly to its PLO is doing the right thing, and the dictionary does
not penalise it for that.

## Deriving a CLO's level

Used by `checklist.md` rules 2.2, 4.7 and 4.8.

1. Classify every verb that names something the student does, including a
   verb in a "to ..." clause, and take the highest level. In "Apply
   statistical tests to evaluate a design change" the student applies and
   evaluates, so the CLO is at Evaluate.
2. A verb whose subject is not the student is not classified ("... models
   and when each applies": the model applies, not the student). A noun is
   not classified either, even when it is spelled like a dictionary verb:
   "design" in "a design review", "plan" in "a floor plan", "development"
   in "a development board".
3. A verb missing from the dictionary is classified by a clear synonym, and
   the reviewer's notes say so — for example "classified 'build' as Create
   by analogy to 'construct'". A synonym match is a normal, expected
   outcome, not a defect in the spec, and never becomes a finding.
4. A CLO with no classifiable verb has no derived level and fails rule 2.2.
   This is the usual symptom of a CLO written as a teaching aim rather than
   a student outcome ("Give students a foundation in ...", "Introduce the
   student to ..."). Report the wording, not a Bloom mismatch.
5. A CLO worded as an aim that still contains classifiable student verbs
   ("So that students have the skills to compare two sorting algorithms")
   passes 2.2
   and takes the level of those verbs. Rule 2.2 checks classifiability
   only.

## Level names on the form

| Level | Thai on the form |
|---|---|
| Remember | จำ |
| Understand | เข้าใจ |
| Apply | นำไปใช้ / ประยุกต์ใช้ |
| Analyze | วิเคราะห์ |
| Evaluate | ประเมิน / ประเมินค่า |
| Create | สร้างสรรค์ |

The Thai form prints a measurement level as `ทฤษฎีการเรียนรู้ของบลูม (<ระดับ>)`,
e.g. `ทฤษฎีการเรียนรู้ของบลูม (เข้าใจ)`; the English rendering prints
`Bloom's taxonomy (Understand)`.

## Thai verbs

For reviewing real Thai-language specs (the synthetic corpus is English).
Each Thai verb is classified through the English dictionary verb beside it.

| Thai | Dictionary verb | Level |
|---|---|---|
| ระบุ | identify | Remember |
| บอก | state | Remember |
| นิยาม / ให้นิยาม | define | Remember |
| อธิบาย | explain | Understand |
| สรุป | summarize | Understand |
| บรรยาย | describe | Understand |
| จำแนกประเภท | classify | Understand |
| อภิปราย | discuss | Understand |
| ประยุกต์ใช้ / นำไปใช้ | apply | Apply |
| ใช้ | use | Apply |
| แก้ปัญหา | solve | Apply |
| คำนวณ | calculate | Apply |
| สาธิต | demonstrate | Apply |
| วิเคราะห์ | analyze | Analyze |
| เปรียบเทียบ | compare | Analyze |
| แยกแยะ | distinguish | Analyze |
| ตรวจสอบ | examine | Analyze |
| เลือก | select | Analyze |
| ประเมิน | evaluate / assess | Evaluate |
| วิจารณ์ | critique | Evaluate |
| ตัดสิน | judge | Evaluate |
| ให้เหตุผลสนับสนุน | justify | Evaluate |
| เสนอแนะ | recommend | Evaluate |
| ออกแบบ | design | Create |
| พัฒนา | develop | Create |
| สร้าง | construct | Create |
| วางแผน | plan | Create |
| ทำงานเป็นทีม | function (convention) | Apply |
| สื่อสาร / นำเสนอ | communicate (convention) | Apply |

Openings that describe what the course gives rather than what the student
does — "ให้นิสิตมี ...", "เพื่อให้นิสิตมีพื้นฐาน / ความรู้ ..." — fail rule
2.2 when no classifiable verb follows. "เพื่อให้นิสิตสามารถ <verb>" ("so that
students can <verb>") is classified by <verb>.

## Method types

Used by `checklist.md` rule 4.9: a method's stated measurement level must be
one its type can evidence on its own. The type is read from the method's
name and from the assessment note.

| Method type | Example names | Highest level it can evidence alone |
|---|---|---|
| Attendance, participation | Attendance, Class participation | None: a stated level fails 4.9 |
| Quiz or written exam | Quiz, Midterm exam, Final exam | Analyze, or higher only when the spec quotes an exam item that sets an Evaluate or Create task |
| Homework or exercise | Homework, Assignment, Problem set, Lab, Lab reports, Exercise | Analyze |
| Report | Report, Case study, Critique report | Evaluate |
| Presentation | Presentation, Demonstration | Evaluate |
| Peer review or critique | Peer review, Peer evaluation, Critique notes, Design review | Evaluate |
| Project or design deliverable | Project, Term project, Capstone, Design document, Project plan, Build deliverable | Create |

A method whose type cannot be read from its name or from the assessment note
is treated as homework.

## How rules 4.7-4.9 use this file

- **4.7** compares a method's stated level with the highest derived level
  among the CLOs it assesses. A method may measure below its CLOs (a quiz at
  Understand for an Apply CLO is normal); it may not claim a level none of
  its CLOs asks for.
- **4.8** checks that each CLO's derived level is reached by at least one of
  its methods.
- **4.9** checks the method type against the table above.
- The order in which they are checked, and what each skips, is the
  precedence list in `checklist.md`.
