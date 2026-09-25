# Program Learning Outcome (PLO) Catalog

> **⚠ PLACEHOLDER — REPLACE WITH THE PROGRAM'S OFFICIAL PLO CATALOG BEFORE ANY
> REAL COMMITTEE USE.** This table is built for testing the plugin. Using it
> for a real committee review would present made-up institutional data as
> authoritative. Swap in the program's own PLO list from its curriculum
> document (same file path, same `PLO ID` column) and everything downstream
> (curriculum-auditor, the batch coverage rollup) keeps working unchanged.

Built on the IEA Washington Accord graduate attribute profile, GAPC version
2021.1 (WA1-WA11; see `tabee-standard.md`), with one PLO per attribute. Each
PLO carries an example tag for the learning-outcome domain(s) of Thailand's
2022 higher-education qualification standards (knowledge, skills, ethics,
character); the program's curriculum document is the authority for the real
tagging. A real program usually has fewer, broader PLOs, each mapped to
several WA attributes.

Curriculum: placeholder, used by every course in `courses/`.

| PLO ID | Statement | WA attribute (GAPC 2021.1) | Thai 2022 domain |
|---|---|---|---|
| PLO1 | Apply knowledge of mathematics, natural science, computing and computer engineering fundamentals to develop solutions to complex engineering problems | WA1 Engineering Knowledge | Knowledge |
| PLO2 | Identify, formulate, research and analyze complex computer engineering problems, reaching substantiated conclusions | WA2 Problem Analysis | Skills |
| PLO3 | Design creative solutions, systems, components or processes that meet identified needs, with appropriate regard for safety, whole-life cost and societal and environmental considerations | WA3 Design/development of solutions | Skills |
| PLO4 | Conduct investigations of complex problems using research methods, including design of experiments and analysis and interpretation of data, to reach valid conclusions | WA4 Investigation | Skills |
| PLO5 | Create, select and apply appropriate techniques, resources and modern engineering and IT tools, recognizing their limitations | WA5 Tool Usage | Skills |
| PLO6 | Analyze and evaluate the sustainable-development impacts of engineering solutions on society, the economy, health and safety, legal frameworks and the environment | WA6 The Engineer and the World | Skills; Ethics |
| PLO7 | Apply ethical principles, commit to professional ethics and norms of engineering practice, and act within relevant national and international laws | WA7 Ethics | Ethics |
| PLO8 | Function effectively as an individual, and as a member or leader in diverse and inclusive teams, face to face, remote and distributed | WA8 Individual and Collaborative Team work | Character |
| PLO9 | Communicate effectively and inclusively on complex engineering activities, in written reports, design documentation and presentations | WA9 Communication | Skills |
| PLO10 | Apply engineering management principles and economic decision-making to one's own work, in teams and in managing projects | WA10 Project Management and Finance | Skills |
| PLO11 | Recognize the need for, and engage in, independent and life-long learning, adapting to new and emerging technologies | WA11 Lifelong learning | Character |

## Validity rule

A course spec's PLO references are **valid** only if every value is either:

- a `PLO ID` that appears verbatim in this table, or
- explicitly empty **with a stated reason** the committee has accepted (rare,
  e.g. a 0-unit seminar with no assessed outcome).

A bare `-` with no reason is **not** a valid empty value; it is a
missing-mapping defect (checklist rules 2.3 and 2.4). The real
`total-cases/2110511.pdf` has this defect in its related-PLO section and on
all three of its CLOs.
