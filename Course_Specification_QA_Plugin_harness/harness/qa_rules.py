"""The plugin's rules as code: checklist.md, bloom-taxonomy.md, plo-catalog.md and the
verdict policy from committee-review-format. No model, no I/O: spec in, drafts out.

A *draft* is a finding without id/source/status; `qa_tools.add_finding` completes it.
"""
from __future__ import annotations

import re

from .spec_parser import BLOOM_LEVELS, POLICY_KEYS, Spec

# Severity defaults, verbatim from references/checklist.md
SEVERITY = {
    "1.1": "blocker", "1.2": "blocker", "2.1": "blocker", "2.2": "blocker", "2.5": "blocker",
    "2.6": "blocker", "3.1": "blocker", "3.2": "blocker", "3.3": "blocker",
    "2.3": "major", "2.4": "major", "3.4": "major", "3.6": "major", "4.3": "major",
    "4.4": "major",
    "3.5": "minor", "4.1": "minor", "4.2": "minor", "4.5": "minor",
}

# references/bloom-taxonomy.md verb -> level lookup
VERBS = {
    "Remember": "define list recall identify name state label recognize",
    "Understand": "explain summarize describe classify interpret discuss translate",
    "Apply": "apply demonstrate implement solve use execute calculate operate",
    "Analyze": "analyze compare differentiate organize deconstruct examine distinguish",
    "Evaluate": "evaluate critique justify argue assess defend recommend judge",
    "Create": "design develop construct formulate produce plan compose devise",
}
VERB_LEVEL = {v: lvl for lvl, words in VERBS.items() for v in words.split()}
LEVEL_RANK = {lvl: i for i, lvl in enumerate(BLOOM_LEVELS, 1)}
# Components that count as a project/design/critique deliverable (checklist 3.6)
DELIVERABLE_WORDS = ("project", "design", "critique", "portfolio", "capstone", "studio", "thesis")
BLOOM_REF = "Bloom's Taxonomy (Anderson & Krathwohl, 2001)"
PLO_REF = "plo-catalog.md / TABEE"

POLICY_RULE = {"attendance": "4.1", "deadlines": "4.2", "academic_integrity": "4.3",
               "plagiarism": "4.4", "ai_tools": "4.5"}
POLICY_NAME = {"attendance": "Attendance policy", "deadlines": "Deadline / late-submission policy",
               "academic_integrity": "Academic integrity statement",
               "plagiarism": "Plagiarism and false-citation statement",
               "ai_tools": "AI Tools & Critical Use statement"}


def draft(rule: str, section: str, quote: str, message: str, fix: str,
          standard_ref: str | None = None) -> dict:
    return {"checklist_rule": rule, "severity": SEVERITY[rule], "section": section,
            "quote": quote, "standard_ref": standard_ref, "message": message,
            "suggested_fix": fix}


# ------------------------------------------------------------------- weights
def weight_report(spec: Spec) -> dict:
    ws = [a.weight for a in spec.assessments]
    total = sum(w for w in ws if w is not None)
    return {"components": [{"component": a.component, "weight": a.weight, "clos": a.clos}
                           for a in spec.assessments],
            "sum": round(total, 6), "delta_from_100": round(total - 100, 6),
            "stated_total": spec.stated_total,
            "stated_total_matches_sum": spec.stated_total is None or spec.stated_total == total}


# ------------------------------------------------------- reviewer: structure
def check_structure(spec: Spec) -> list[dict]:
    """Checklist items 1.x, 2.1-2.3, 2.5, 3.1-3.5, 4.x (presence and arithmetic)."""
    out: list[dict] = []
    s1, s2, s3, s4 = ("Section 1 -> Course Information", "Section 2 -> Learning Outcomes",
                      "Section 3 -> Assessment", "Section 4 -> Course Policies")

    if not spec.course_code or not re.fullmatch(r"[A-Za-z]{2,4}\s?-?\d{3,4}", spec.course_code):
        out.append(draft("1.1", s1, spec.course_code or "(missing)",
                         "Course code is missing or not in a recognisable format.",
                         "State the registered course code, e.g. CPE201."))
    if not spec.course_name:
        out.append(draft("1.2", s1, "(missing)", "Course name is missing.",
                         "Add the official course name under Section 1."))

    if not spec.clos:
        out.append(draft("2.1", s2, "(no CLO table found)", "No CLOs are listed.",
                         "Add a CLO table with description, Bloom level and PLO columns."))
    for c in spec.clos:
        if not c.description.strip():
            out.append(draft("2.2", f"{s2} -> {c.id}", c.raw, f"{c.id} has an empty description.",
                             f"Write the outcome statement for {c.id}."))
        if c.bloom.strip().capitalize() not in BLOOM_LEVELS:
            out.append(draft("2.3", f"{s2} -> {c.id}", c.raw,
                             f"{c.id} Bloom level {c.bloom!r} is missing or not one of "
                             f"{', '.join(BLOOM_LEVELS)}.",
                             f"State one of the six Bloom levels for {c.id}."))
        if not c.plos:
            out.append(draft("2.5", f"{s2} -> {c.id}", c.raw,
                             f"{c.id} is not mapped to any PLO (PLO column empty or '-').",
                             f"Map {c.id} to at least one PLO from plo-catalog.md.",
                             standard_ref=PLO_REF))

    if not spec.assessments:
        out.append(draft("3.1", s3, "(no assessment table found)",
                         "No assessment components with weights are listed.",
                         "Add an assessment table with component, weight and mapped CLOs."))
    for a in spec.assessments:
        if a.weight is None or a.weight < 0:
            out.append(draft("3.2", f"{s3} -> {a.component}", a.raw,
                             f"Weight of {a.component!r} is not a non-negative number.",
                             "Give the component a numeric weight >= 0."))
        if not a.clos:
            out.append(draft("3.4", f"{s3} -> {a.component}", a.raw,
                             f"Assessment component {a.component!r} maps to no CLO.",
                             "List the CLOs this component evidences."))
    if spec.assessments:
        w = weight_report(spec)
        if w["sum"] != 100:
            quote = "; ".join(f"{a.component} {a.weight:g}" for a in spec.assessments
                              if a.weight is not None)
            if spec.stated_total is not None:
                quote += f" -- \"**Total: {spec.stated_total:g}**\""
            gap = "shortfall" if w["sum"] < 100 else "excess"
            out.append(draft("3.3", f"{s3} -> Assessment table", quote,
                             f"Assessment weights sum to {w['sum']:g}, not 100 "
                             f"({gap} of {abs(w['delta_from_100']):g}).",
                             "Adjust a component weight or add a missing component so the "
                             "table sums to exactly 100."))
    if spec.rubric_items == 0:
        out.append(draft("3.5", s3, "(no 'Scoring Criteria' section with items)",
                         "No scoring criteria / rubric section is present.",
                         "Add a scoring-criteria checklist, even a short one."))

    for key, rule in POLICY_RULE.items():
        if key not in spec.policies:
            out.append(draft(rule, s4, "(missing)", f"{POLICY_NAME[key]} is missing.",
                             f"Add the {POLICY_NAME[key].lower()} to Section 4."))
    return out


# --------------------------------------------------------------- auditor: Bloom
def lookup_verb(word: str) -> str | None:
    return VERB_LEVEL.get(word.lower().strip(" ,.;:"))


def leading_verbs(description: str) -> list[str]:
    """Verbs at the start of a CLO, including chains: 'Design, develop and evaluate ...'."""
    verbs = []
    for tok in re.findall(r"[A-Za-z']+|,", description):
        t = tok.lower()
        if t in {",", "and", "or"} and verbs:
            continue
        if t in VERB_LEVEL:
            verbs.append(t)
        else:
            break
    return verbs


def classify_clo(description: str) -> dict:
    verbs = leading_verbs(description)
    if not verbs:
        first = (re.findall(r"[A-Za-z']+", description) or [""])[0].lower()
        return {"verbs": [], "first_word": first, "level": None, "literal": False}
    top = max(verbs, key=lambda v: LEVEL_RANK[VERB_LEVEL[v]])  # highest level, per skill
    return {"verbs": verbs, "level": VERB_LEVEL[top], "driving_verb": top, "literal": True}


def check_bloom(spec: Spec) -> list[dict]:
    """Checklist 2.4 (stated level vs verb) and 3.6 (Evaluate/Create evidence)."""
    out, sec = [], "Section 2 -> Learning Outcomes"
    for c in spec.clos:
        cls = classify_clo(c.description)
        if not cls["literal"]:
            continue  # unknown verb: surfaced by `bloom_review`, needs model judgment
        eff, stated = cls["level"], c.bloom.strip().capitalize()
        verb = cls["driving_verb"]
        if stated in LEVEL_RANK and eff != stated:
            over = LEVEL_RANK[stated] > LEVEL_RANK[eff]
            d = draft("2.4", f"{sec} -> {c.id}", c.raw,
                      f"{c.id} states {stated} but verb '{verb}' is {eff}-level "
                      f"({'over' if over else 'under'}-claimed).",
                      f"Reword {c.id} with a verb that supports {stated}, or restate its level "
                      f"as {eff}.",
                      standard_ref=f"{BLOOM_REF}: verb '{verb}' = {eff}, but CLO states {stated}")
            if not over:
                d["severity"] = "minor"  # bloom-verb-rules step 3: under-claiming is Minor
            out.append(d)
        if eff in ("Evaluate", "Create"):
            mapped = [a for a in spec.assessments if c.id in a.clos]
            if mapped and not any(any(w in a.component.lower() for w in DELIVERABLE_WORDS)
                                  for a in mapped):
                out.append(draft(
                    "3.6", f"Section 3 -> Assessment table ({c.id})",
                    "; ".join(a.raw for a in mapped),
                    f"{c.id} is {eff}-level but is mapped only to "
                    f"{', '.join(a.component for a in mapped)}; no project/design/critique "
                    "deliverable evidences it.",
                    f"Map {c.id} to a project, design or critique deliverable.",
                    standard_ref=f"{BLOOM_REF}: assessment-congruence table, {eff} level"))
    return out


def bloom_review(spec: Spec) -> list[dict]:
    """Per-CLO table: what the rules decided, and which CLOs need the model's judgment."""
    rows = []
    for c in spec.clos:
        cls = classify_clo(c.description)
        stated = c.bloom.strip().capitalize()
        if not cls["literal"]:
            status = "needs_model_judgment"
        elif stated not in LEVEL_RANK:
            status = "stated_level_invalid"
        elif cls["level"] == stated:
            status = "match"
        else:
            status = "over_claimed" if LEVEL_RANK[stated] > LEVEL_RANK[cls["level"]] \
                else "under_claimed"
        rows.append({"clo": c.id, "description": c.description, "stated": stated,
                     "verb_level": cls.get("level"), "verbs": cls.get("verbs", []),
                     "first_word": cls.get("first_word"), "status": status})
    return rows


# ---------------------------------------------------------------- auditor: PLO
def validate_plo_ids(ids: list[str], catalog: dict[str, str]) -> dict:
    valid = [i for i in ids if i.upper() in catalog]
    return {"valid": valid, "invalid": [i for i in ids if i.upper() not in catalog]}


def check_plo(spec: Spec, catalog: dict[str, str]) -> list[dict]:
    """Checklist 2.5 (empty) and 2.6 (dangling ID)."""
    out, sec = [], "Section 2 -> Learning Outcomes"
    for c in spec.clos:
        if not c.plos:
            out.append(draft("2.5", f"{sec} -> {c.id}", c.raw,
                             f"{c.id} is not mapped to any PLO (PLO column empty or '-').",
                             f"Map {c.id} to at least one PLO from plo-catalog.md.",
                             standard_ref=f"{PLO_REF}: every CLO must map to a PLO"))
        for p in validate_plo_ids(c.plos, catalog)["invalid"]:
            out.append(draft("2.6", f"{sec} -> {c.id}", c.raw,
                             f"{c.id} cites PLO ID '{p}', which does not exist in the catalog "
                             "(dangling reference).",
                             f"Replace '{p}' with a PLO ID from plo-catalog.md.",
                             standard_ref=f"plo-catalog.md: PLO code '{p}' does not exist"))
    return out


def plo_coverage(specs: list[Spec], catalog: dict[str, str]) -> dict:
    """Program rollup. A PLO cited only by a course with invalid mappings is 'unverified'."""
    covered: dict[str, list[str]] = {p: [] for p in catalog}
    unverified: dict[str, list[str]] = {p: [] for p in catalog}
    for s in specs:
        clean = all(c.plos and not validate_plo_ids(c.plos, catalog)["invalid"] for c in s.clos)
        for c in s.clos:
            for p in validate_plo_ids(c.plos, catalog)["valid"]:
                bucket = covered if clean else unverified
                if s.course_code not in bucket[p.upper()]:
                    bucket[p.upper()].append(s.course_code)
    return {"covered": {p: v for p, v in covered.items() if v},
            "unverified_only": {p: v for p, v in unverified.items() if v and not covered[p]},
            "gaps": [p for p in catalog if not covered[p] and not unverified[p]]}


# --------------------------------------------------------------------- verdict
def compute_verdict(findings: list[dict]) -> dict:
    """The entire verdict logic (committee-review-format policy table)."""
    openf = [f for f in findings if f.get("status", "open") == "open"]
    count = {sev: sum(1 for f in openf if f["severity"] == sev)
             for sev in ("blocker", "major", "minor")}
    verdict = "RETURN" if count["blocker"] else "REVISE" if count["major"] else "APPROVE"
    return {"verdict": verdict, "open_counts": count,
            "open_blocker_ids": [f["id"] for f in openf if f["severity"] == "blocker"]}
