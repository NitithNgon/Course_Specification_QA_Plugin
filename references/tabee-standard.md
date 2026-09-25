# TABEE, the Washington Accord and Thai standards (reference summary)

> **Status:** summary for QA purposes, researched on 2026-09-25. Every claim
> names its source, and the table at the end says whether it was read from a
> primary source. Re-verify the unverified claims against the official
> documents before using this file in an accreditation submission.

## TABEE

TABEE (Thailand Accreditation Board of Engineering Education) accredits
engineering programs in Thailand. According to its website, it was
established in 2015 as an autonomous part of the Council of Engineers
Thailand (COET), and its evaluation is based on the IEA Graduate Attributes
and Professional Competencies (GAPC) under the Washington Accord.
*(Unverified: read from search-result text of tabee.coe.or.th; the site did
not resolve from the research environment.)*

## Washington Accord status

- Thailand, through the Council of Engineers Thailand (COET), is listed as a
  **provisional signatory** of the Washington Accord, not a full signatory.
  *(Primary: IEA Washington Accord page.)*
- Provisional status dates from 2019. *(Unverified: TABEE site text.)*
- Mutual recognition under the Accord covers programs accredited by full
  signatories. Check the IEA rules and procedures for what provisional status
  allows before claiming recognition for a TABEE-accredited program.

## IEA graduate attributes (GAPC version 2021.1)

Approved on 21 June 2021, replacing the 2013 version. *(Primary: IEA GAPC
2021.1 PDF.)* The Washington Accord profile has 11 attributes:

| # | Attribute | Short gloss |
|---|---|---|
| WA1 | Engineering Knowledge | Apply mathematics, natural science, computing and engineering fundamentals and a specialization to develop solutions to complex engineering problems |
| WA2 | Problem Analysis | Identify, formulate, research and analyze complex engineering problems, reaching substantiated conclusions, with holistic consideration of sustainable development |
| WA3 | Design/development of solutions | Design creative solutions and systems, components or processes for identified needs, considering health and safety, whole-life cost, net zero carbon, and resource, cultural, societal and environmental factors |
| WA4 | Investigation | Conduct investigations of complex problems using research methods, including design of experiments and analysis and interpretation of data |
| WA5 | Tool Usage | Create, select and apply, and recognize the limitations of, techniques, resources and modern engineering and IT tools, including prediction and modelling |
| WA6 | The Engineer and the World | Analyze and evaluate sustainable-development impacts on society, the economy, sustainability, health and safety, legal frameworks and the environment |
| WA7 | Ethics | Apply ethical principles, commit to professional ethics and norms, adhere to national and international laws, and understand the need for diversity and inclusion |
| WA8 | Individual and Collaborative Team work | Function effectively as an individual and as a member or leader in diverse and inclusive teams, in multi-disciplinary, face-to-face, remote and distributed settings |
| WA9 | Communication | Communicate effectively and inclusively on complex engineering activities, including reports, design documentation and presentations |
| WA10 | Project Management and Finance | Apply engineering management principles and economic decision-making to one's own work, as a team member and leader, and to manage projects |
| WA11 | Lifelong learning | Recognize the need for, and be prepared for, independent life-long learning, adaptability to new technologies, and critical thinking about technological change |

WA6 covers what the 2013 profile split between "The Engineer and Society"
and "Environment and Sustainability"; a PLO catalog built on the 2013
twelve-attribute list is out of date.

## Thai higher-education standards

- The Ministerial Regulation on Higher Education Qualification Standards
  B.E. 2565 (2022) requires graduates' learning outcomes to cover at least
  four domains: knowledge (ความรู้), skills (ทักษะ), ethics (จริยธรรม) and
  character (ลักษณะบุคคล). It replaced the five domains of the Thai
  Qualifications Framework for Higher Education (TQF:HEd).
  *(Unverified: confirmed through secondary sources; the Royal Gazette PDF
  returned HTTP 403 to the research environment.)*
- The Ministry of Higher Education, Science, Research and Innovation
  published the detail in the announcement "รายละเอียดผลลัพธ์การเรียนรู้ตาม
  มาตรฐานคุณวุฒิระดับอุดมศึกษา พ.ศ. 2565", listed on 22 July 2022.
  *(Primary: MHESI page; the linked PDF itself was not read.)*
- Legacy framework, for curricula not yet revised: TQF:HEd's five domains
  were Ethics and Moral Development; Knowledge; Cognitive Skills;
  Interpersonal Skills and Responsibility; Numerical Analysis, Communication
  and Information Technology Skills. *(Carried over from the previous version
  of this file; unverified.)*

## Where domains live in this plugin

The official CU course-specification form (2025) has no per-CLO domain
field, so this plugin does not check domain tagging course by course. Each
PLO in `plo-catalog.md` carries its domain tag instead, and the batch
coverage rollup can be read per domain from there.

## What curriculum-auditor checks against this file

- Every PLO ID a course cites exists in `plo-catalog.md` (checklist 2.5),
  and the PLOs on the CLOs match the course's related-PLO list (2.6). The
  presence of PLO IDs (2.3, 2.4) is course-reviewer's check.
- In batch mode (`/review-spec --all`), every PLO in the catalog is covered by
  at least one course. A PLO covered by no course is a gap in the
  course-to-PLO mapping a TABEE self-study relies on; a PLO claimed only by
  courses with an open blocker is reported as "claimed, not yet approved".

## Verification status

| Claim | Source | Read from the primary source? |
|---|---|---|
| GAPC 2021.1, approved 21 June 2021, WA1-WA11 as listed | IEA GAPC 2021.1 PDF | Yes |
| Thailand (COET) is a provisional Washington Accord signatory | IEA Washington Accord page | Yes |
| Provisional since 2019 | tabee.coe.or.th (search-result text) | No |
| TABEE founded in 2015 within COET; evaluation based on GAPC | tabee.coe.or.th (search-result text) | No |
| Four learning-outcome domains under the B.E. 2565 regulation | Secondary sources citing the Royal Gazette | No |
| MHESI announcement title and listing date | MHESI page | Yes |
| TQF:HEd five legacy domains | Previous version of this file | No |

Sources:

- IEA GAPC 2021.1: https://www.internationalengineeringalliance.org/assets/Uploads/IEA-Graduate-Attributes-and-Professional-Competencies-2021.1-Sept-2021.pdf
- IEA Washington Accord signatories: https://www.internationalengineeringalliance.org/accords/washington-accord
- TABEE Washington Accord page: https://tabee.coe.or.th/washington-accord/
- Royal Gazette, Higher Education Qualification Standards B.E. 2565: https://www.ratchakitcha.soc.go.th/DATA/PDF/2565/A/020/T_0028.PDF
- MHESI announcement page: https://www.ops.go.th/en/role/edu-standard/item/6940-2022-07-22-02-54-49
