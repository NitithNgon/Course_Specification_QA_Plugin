# Course specification form (English rendering)

This is the official Chulalongkorn University course-specification form
(ประมวลรายวิชา) as used by `total-cases/2110511.pdf` and
`total-cases/2110651.pdf`, rendered in English. The synthetic specs in
`courses/` follow the skeleton below exactly. Real specs arrive as Thai PDFs
carrying the labels shown in brackets; `checklist.md` names fields by the
English label, and the rules apply to both.

Conventions, as on the real form:

- A field with no content is written `-`.
- CLOs are numbered CLO1, CLO2, ... and cited by that ID in the content and
  assessment tables. (The Thai form sometimes repeats the CLO's full text
  instead; treat the text as the ID it belongs to.)
- A measurement level is written `Bloom's taxonomy (<Level>)`; the Thai form
  prints `ทฤษฎีการเรียนรู้ของบลูม (<ระดับ>)`. The level names and their Thai
  equivalents are in `bloom-taxonomy.md`.
- Percentages are written with two decimals, as the form prints them.
- The English rendering gives the course description in English only; the
  Thai form prints it in Thai and English. Rule 1.7 needs a description in
  either language.

## Where the form gate (rule F.1) looks

| Part F.1 needs | Section of the form |
|---|---|
| CLO table with a related-PLO column | Course learning outcomes (ผลลัพธ์การเรียนรู้ระดับรายวิชา) |
| Assessment table with measurement-level and related-CLO columns | Assessment (การประเมินผลการเรียน) |
| Grading section with grade thresholds | Grading (การตัดเกรด) |

Older numbered syllabi (items 1-17, e.g. `total-cases/2110555.pdf` and
`2110743.pdf`) and instructor handouts (`2110514.pdf`, `2110576.pdf`) have
none of the three in this form, and fail F.1.

## Skeleton

```markdown
# Course Specification (ประมวลรายวิชา)

## Course information (ข้อมูลรายวิชา)

| Field | Value |
|---|---|
| Course code (รหัสรายวิชา) | CPE000 |
| Credits (หน่วยกิต) | 3 (3-0-6) |
| Course title, Thai (ชื่อรายวิชา ภาษาไทย) | ... |
| Course title, English (ชื่อรายวิชา ภาษาอังกฤษ) | ... |
| Faculty (คณะ/สถาบัน) | Faculty of Engineering |
| Department (ภาควิชา) | Department of Computer Engineering |
| Program (สาขาวิชา) | ... |
| Course type (ประเภทรายวิชา) | Bi-semester (regular program) |
| Semester (ภาคการศึกษา) | First semester |
| Academic year (ปีการศึกษา) | 2026 |
| Course coordinator (ผู้ประสานงานรายวิชา) | ... |
| Registration conditions (เงื่อนไขในการลงทะเบียน) | ... |
| Degree level (ระดับปริญญา) | Bachelor's |
| Related curricula (หลักสูตรที่เกี่ยวข้อง) | ... |
| Course status (สถานะรายวิชา) | Required |

### Instructors (ผู้สอน / สตาฟฟ์)

| Section | Instructor |
|---|---|
| 1 | ... |

### Course description (คำบรรยายรายวิชา)

...

## Program learning outcomes related to the course (ผลลัพธ์การเรียนรู้ระดับหลักสูตรที่เกี่ยวข้องกับรายวิชา)

- PLO1: ...

## Course learning outcomes (ผลลัพธ์การเรียนรู้ระดับรายวิชา)

| CLO | Course learning outcome | Related PLO |
|---|---|---|
| CLO1 | ... | PLO1 |

## Content (เนื้อหา)

| Week | Topic | CLO |
|---|---|---|
| 1 | ... | CLO1 |

Content note (หมายเหตุเกี่ยวกับเนื้อหารายวิชา): ...

## Teaching media (สื่อที่ใช้ในการเรียนการสอน)

- ...

## Communication channels / LMS (ช่องทางการสื่อสาร / ระบบ LMS)

| Type | Name / URL | Note |
|---|---|---|
| Learning management system | myCourseVille | ... |

## Assessment (การประเมินผลการเรียน)

| Method | Measurement level | Related CLO | Percent |
|---|---|---|---|
| ... | Bloom's taxonomy (Apply) | CLO1 | 20.00 |

### Assessment note (หมายเหตุเกี่ยวกับการประเมินผลการเรียน)

...

## Grading (การตัดเกรด)

| Field | Value |
|---|---|
| Grading system (ระบบเกรด) | Letter grade (A-F) |
| Grading method (วิธีตัดเกรด) | Criterion-referenced |
| Minimum passing level (ระดับต่ำสุดในการผ่าน, MPL) | 0 |

| Grade | Threshold |
|---|---|
| A | ≥ 80 |
| B+ | ≥ 75 |
| B | ≥ 70 |
| C+ | ≥ 65 |
| C | ≥ 60 |
| D+ | ≥ 55 |
| D | ≥ 50 |
| F | Otherwise |

## Reading list (รายการเอกสารอ่านประกอบ)

| Type | Title | Note |
|---|---|---|
| Book | ... | ... |

## Teaching evaluation (การประเมินผลการเรียนการสอน)

| Field | Value |
|---|---|
| Evaluation channel (ประเมินผลการเรียนการสอนผ่านช่องทาง) | ... |
| Changes after the previous evaluation (รายละเอียดการปรับปรุงจากการประเมินครั้งที่ผ่านมา) | ... |

## Course quality control (การควบคุมคุณภาพรายวิชา)

| Field | Value |
|---|---|
| Response to student complaints (การตอบสนองต่อข้อตำหนิ/คำร้องเรียนจากนิสิต) | ... |

## AI-related learning (การจัดการเรียนรู้เกี่ยวกับ AI)

| Field | Value |
|---|---|
| AI topics taught (หัวข้อเกี่ยวกับ AI ที่สอนในรายวิชานี้) | None |
| Total hours (จำนวนชั่วโมงรวม) | 0 |
| Learning strategy (กลยุทธ์การเรียนรู้ที่ใช้ในการสอนหัวข้อเกี่ยวกับ AI) | - |
| Assessment strategy (กลยุทธ์การประเมินผลที่ใช้สำหรับหัวข้อเกี่ยวกับ AI) | - |

## SDG alignment (ความสอดคล้องกับเป้าหมายการพัฒนาที่ยั่งยืน)

| No. | Goal |
|---|---|
| 1 | Goal 4: Quality education |
```
