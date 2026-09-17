# Review Note — CPE201: Data Structures and Algorithms

**Verdict:** APPROVE

## Findings

### [MINOR] 2.5 (PLO mapping — pedagogical-fit judgment call per plo-mapping-standard skill, not a checklist.md validity failure) — Section 2 -> Learning Outcomes table, CLO2 row
> CLO2 | Apply appropriate data structures to solve a given programming problem | Apply | PLO3

PLO3 is a technically valid PLO code (exists verbatim in plo-catalog.md), so this is NOT a dangling/missing-mapping defect. It is flagged only as a pedagogical-fit judgment call, per the plo-mapping-standard skill's allowance for Minor advisory notes on technically-valid-but-questionable mappings. CLO2's verb is Bloom-level Apply ("apply appropriate data structures to solve a given programming problem" — selecting/using an existing structure for a given problem), whereas PLO3's statement is phrased around designing/developing systems and components to meet specified requirements, an outcome more naturally evidenced by Create-level work (bloom-taxonomy.md lists design/develop/construct/formulate as Create-level verbs). Selecting an appropriate existing data structure is a narrower, lower-order slice of "design" than PLO3's full statement implies, which is a debatable but not obviously-wrong fit. Note for context: CLO1 already maps to PLO1 ("Apply mathematics, science, and computer engineering fundamentals to solve engineering problems"), whose wording is arguably the closer verbatim match to CLO2's own phrase ("solve a given programming problem"), so this may reflect an intentional instructor choice to spread PLO coverage across CLO1/CLO2/CLO3 rather than a genuine mapping error.

**Fix:** No change required if the PLO spread across CLO1/CLO2/CLO3 is intentional curriculum design. If not intentional, consider either (a) re-mapping CLO2 to PLO1 for a closer wording fit, or (b) raising CLO2's verb/assessment to an explicit design-level task (e.g. "design and justify a data-structure choice for problem X") so the CLO more fully evidences PLO3's Design/Development attribute.

## Standards cited
- plo-catalog.md: PLO3 = "Design software/hardware systems and components that meet specified requirements" (WA Attribute 3, Design/Development of Solutions); cross-ref bloom-taxonomy.md verb dictionary (design/develop/construct = Create level)
