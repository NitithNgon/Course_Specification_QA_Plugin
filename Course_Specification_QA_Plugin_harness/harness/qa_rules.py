"""references/checklist.md as code: the 41 rules, the precedence list and the verdict policy.

Pure functions over a parsed Spec. No model, no file writes. Severity and owner are never
written here: `draft()` reads them from checklist.md through data_store.checklist(), so the
rulebook file stays the single source of truth.

What still needs judgment, and is therefore left to the model (see qa_tools):
  - a CLO verb that is neither in bloom-taxonomy.md nor in SYNONYMS below (set_clo_level)
  - 2.7 advisory "obvious poor fit" findings (add_finding)
  - an exam that quotes an Evaluate/Create item (4.9 exception in bloom-taxonomy.md)
"""
from __future__ import annotations

import re

from . import data_store as ds
from .spec_parser import Method, Spec, clo_ids, is_empty, plo_ids

RANK = {lvl: i for i, lvl in enumerate(ds.LEVELS, 1)}
BLOOM_REF = "Bloom's Taxonomy (Anderson & Krathwohl, 2001)"

# Verbs outside bloom-taxonomy.md, classified "by a clear synonym" (deriving rule 3). This is
# the harness's own judgment table; extend it, or let the model decide with set_clo_level.
SYNONYMS = {
    "build": "construct", "create": "construct", "diagnose": "examine", "document": "describe",
    "answer": "explain", "investigate": "examine",
}
# Words after and/or/"," that make a dictionary verb a noun modifier ("design decisions").
NOUN_HEADS = {"decision", "decisions", "review", "reviews", "document", "documents", "team",
              "teams", "board", "boards", "choice", "choices", "pattern", "patterns", "phase",
              "phases", "process", "processes", "principle", "principles", "rule", "rules"}
VERB_TRIGGERS = {"to", "can", "will", "must", "should", "could"}
EXEMPT_WORDS = ("attendance", "participation")


# ===================================================================== helpers
def draft(rule: str, section: str, quote: str, message: str, fix: str,
          standard_ref: str | None = None, line: int | None = None) -> dict:
    r = ds.checklist()[rule]
    return {"checklist_rule": rule, "severity": r["severity"], "source_agent": r["owner"],
            "section": section + (f" (line {line})" if line else ""), "quote": quote,
            "standard_ref": standard_ref, "message": message, "suggested_fix": fix}


def is_exempt(m: Method) -> bool:
    return any(w in m.name.lower() for w in EXEMPT_WORDS)


def is_bonus(m: Method) -> bool:
    return "bonus" in m.name.lower()


def method_type(m: Method) -> tuple[str, str | None]:
    """(type, highest level it can evidence alone) by the longest matching example name."""
    name = m.name.lower()
    best = None
    for typ, examples, top in ds.bloom()["method_types"]:
        for ex in examples:
            if ex in name and (best is None or len(ex) > best[0]):
                best = (len(ex), typ, top)
    if best is None:
        hw = next(t for t in ds.bloom()["method_types"] if t[0].lower().startswith("homework"))
        return hw[0], hw[2]          # "treated as homework" (bloom-taxonomy.md)
    return best[1], best[2]


def fmt(x: float) -> str:
    return f"{x:g}"


# ============================================================ CLO level derivation
def lookup(word: str) -> tuple[str, str] | None:
    """(level, how) for a base-form verb: dictionary, convention, or synonym of X."""
    verbs = ds.bloom()["verbs"]
    w = word.lower()
    if w in verbs:
        return verbs[w]
    if w in SYNONYMS and SYNONYMS[w] in verbs:
        return verbs[SYNONYMS[w]][0], f"synonym of {SYNONYMS[w]}"
    return None


def _lemma(word: str) -> str | None:
    """Base form of an inflected verb, if one is known."""
    if lookup(word):
        return word
    cands = []
    if word.endswith("ing"):
        stem = word[:-3]
        cands = [stem, stem + "e"] + ([stem[:-1]] if len(stem) > 2 and stem[-1] == stem[-2] else [])
    elif word.endswith("ies"):
        cands = [word[:-3] + "y"]
    elif word.endswith("es"):
        cands = [word[:-2], word[:-1]]
    elif word.endswith("s"):
        cands = [word[:-1]]
    return next((c for c in cands if lookup(c)), None)


def derive_clo(text: str) -> dict:
    """bloom-taxonomy.md 'Deriving a CLO's level', as a positional heuristic.

    A word is read as a student verb when it opens the CLO, follows to/can/will, follows
    and/or/',' after a student verb (unless a noun head follows: 'design decisions'), or is an
    -ing participle of a known verb ('using', 'documenting'). Nouns elsewhere ('algorithm
    designs', 'query plans') and verbs with another subject ('a scene that applies') are skipped.
    """
    toks = re.findall(r"[A-Za-z][A-Za-z'-]*|,", text)
    low = [t.lower() for t in toks]
    verbs, seen_verb = [], False
    for i, w in enumerate(low):
        if w == ",":
            continue
        prev = low[i - 1] if i else None
        nxt = low[i + 1] if i + 1 < len(low) else ""
        position = (i == 0 or prev in VERB_TRIGGERS
                    or (seen_verb and prev in {"and", "or", ","} and nxt not in NOUN_HEADS)
                    or (w.endswith("ing") and prev not in {"a", "an", "the"}))
        if not position:
            continue
        base = _lemma(w)
        if base is None or (w.endswith("ing") and base == w):
            continue
        level, how = lookup(base)
        verbs.append({"word": toks[i], "verb": base, "level": level, "how": how})
        seen_verb = True
    level = max((v["level"] for v in verbs), key=RANK.get, default=None)
    return {"verbs": verbs, "level": level,
            "first_word": low[0] if low else "", "classifiable": bool(verbs)}


def clo_levels(spec: Spec, overrides: dict | None = None) -> dict[str, dict]:
    """Derived level per CLO; a recorded model judgment (set_clo_level) wins over the heuristic."""
    out = {}
    for c in spec.clos:
        d = derive_clo(c.text)
        if overrides and c.id in overrides:
            o = overrides[c.id]
            d = {**d, "level": o.get("level"), "classifiable": o.get("level") is not None,
                 "override": o}
        out[c.id] = d
    return out


# ================================================================= F.1 gate
def form_gate(spec: Spec) -> list[str]:
    """Names of the form parts F.1 cannot locate (empty list = on the form)."""
    missing = []
    if not spec.clo_table:
        missing.append("the CLO table with a related-PLO column")
    if not spec.assessment_table:
        missing.append("the assessment table with measurement-level and related-CLO columns")
    if not spec.grade_table:
        missing.append("the grading section with grade thresholds")
    return missing


def f1_failed(spec: Spec) -> bool:
    return bool(form_gate(spec))


# ===================================================== course-reviewer rules
def _row_quote(ln) -> str:
    return ln.text.strip()


def _field_rule(spec, out, rule, section_key, section_label, name, label, fix, ok=None):
    v = spec.field(section_key, name)
    good = v is not None and not is_empty(v[0]) and (ok(v[0]) if ok else True)
    if not good:
        quote = _row_quote(v[1]) if v else "(absent)"
        out.append(draft(rule, f"{section_label}, row \"{label}\"", quote,
                         f"{label} is {'not stated' if not v or is_empty(v[0]) else 'not valid'}.",
                         fix, line=v[1].no if v else None))


def _section_rule(spec, out, rule, key, label, fix):
    s = spec.sec(key)
    if s is None:
        out.append(draft(rule, f"{label} section", "(absent)", f"The {label} section is missing.", fix))
    elif s.is_dash():
        out.append(draft(rule, f"{label} section", "-", f"The {label} section holds only '-'.", fix,
                         line=s.dash_line().no))


def weight_report(spec: Spec) -> dict:
    counted = [m for m in spec.methods if not is_bonus(m)]
    total = sum(m.weight for m in counted if m.weight is not None)
    return {"components": [{"method": m.name, "weight": m.weight, "line": m.line.no,
                            "bonus": is_bonus(m)} for m in spec.methods],
            "sum": round(total, 6), "delta_from_100": round(total - 100, 6),
            "arithmetic": " + ".join(fmt(m.weight) for m in counted if m.weight is not None)
                          + f" = {fmt(total)}",
            "bonus_excluded": [m.name for m in spec.methods if is_bonus(m)],
            "splits": splits(spec)}


_PART = re.compile(r"^(?P<label>.*?)\s*\(?\s*(?P<a>\d+(?:\.\d+)?)\s*(?:[×x*]\s*(?P<b>\d+(?:\.\d+)?))?\s*\)?\s*$")


def splits(spec: Spec) -> list[dict]:
    """Sub-part splits stated in the assessment note: '- <Method> ...: part n, part n' or 'a (n) + b (n)'."""
    out = []
    for ln in spec.assessment_note():
        text = ln.text.strip().lstrip("-* ").strip()
        m = next((m for m in spec.methods if m.name and text.lower().startswith(m.name.lower())), None)
        if not m or ":" not in text:
            continue
        body = text.split(":", 1)[1].strip().rstrip(".")
        pieces = [p.strip() for p in re.split(r"\s*\+\s*|,\s*|;\s*", body) if p.strip()]
        parts = {}
        for p in pieces:
            pm = _PART.match(p)
            if not pm or not pm["label"]:
                parts = {}
                break
            val = float(pm["a"]) * (float(pm["b"]) if pm["b"] else 1)
            parts[pm["label"].strip().lower()] = val
        if len(parts) >= 2:
            out.append({"method": m.name, "weight": m.weight, "line": ln.no, "quote": ln.text.strip(),
                        "parts": parts, "sum": round(sum(parts.values()), 6)})
    return out


def _policy_present(spec: Spec, pattern: str) -> bool:
    body = spec.text_outside("ai-related learning", "sdg alignment", "assessment", "content")
    note = spec.assessment_note()
    return any(re.search(pattern, l.text, re.I) for l in body + note)


def check_structure(spec: Spec, file_stem: str | None = None) -> list[dict]:
    """Every rule owned by course-reviewer, in table order, with the precedence list."""
    out: list[dict] = []
    missing = form_gate(spec)
    if missing:                                   # precedence 1
        out.append(draft("F.1", "Whole document", spec.lines[0].strip() if spec.lines else "(empty)",
                         "The document is not on the official course-specification form. Missing: "
                         + "; ".join(missing) + ".",
                         "Resubmit the specification on the official CU course-specification form "
                         "(references/course-spec-template.md).", line=1))
        return out

    CI = "Course information"
    info = spec.info()
    code = info.get("course code")
    if code is None or is_empty(code[0]):
        out.append(draft("1.1", f"{CI}, row \"Course code\"", _row_quote(code[1]) if code else "(absent)",
                         "Course code is missing.", "State the registered course code.",
                         line=code[1].no if code else None))
    elif file_stem and code[0].strip().upper() != file_stem.upper():
        out.append(draft("1.1", f"{CI}, row \"Course code\"", _row_quote(code[1]),
                         f"Course code {code[0].strip()} does not match the file name {file_stem}.",
                         "Make the course code and the file name agree.", line=code[1].no))

    th, en = info.get("course title, thai"), info.get("course title, english")
    has_th, has_en = th and not is_empty(th[0]), en and not is_empty(en[0])
    if not has_th and not has_en:
        out.append(draft("1.2", f"{CI}, course title rows", "(absent)", "No course title is given.",
                         "State the course title in Thai and English."))
    elif not (has_th and has_en):
        gap = en if not has_en else th
        out.append(draft("1.3", f"{CI}, row \"Course title, {'English' if not has_en else 'Thai'}\"",
                         _row_quote(gap[1]) if gap else "(absent)",
                         f"The course title is not given in {'English' if not has_en else 'Thai'}.",
                         "Give the course title in both Thai and English.", line=gap[1].no if gap else None))

    _field_rule(spec, out, "1.4", "course information", CI, "credits", "Credits",
                "State credits as N (L-P-S), e.g. 3 (3-0-6).",
                ok=lambda v: re.fullmatch(r"\d+\s*\(\d+-\d+-\d+\)", v.strip()) is not None)

    def multi(rule, names, fix):
        gaps, first = [], None
        for key, label in names:
            if key == "course description":
                s = spec.sec("course description")
                if s is None or s.is_dash():
                    gaps.append(label)
                    first = first or (s.dash_line() if s else None)
                continue
            v = info.get(key)
            if v is None or is_empty(v[0]):
                gaps.append(label)
                first = first or (v[1] if v else None)
        if gaps:
            out.append(draft(rule, f"{CI}: " + ", ".join(gaps), _row_quote(first) if first else "(absent)",
                             "Not stated: " + ", ".join(gaps) + ".", fix, line=first.no if first else None))

    multi("1.5", [("faculty", "Faculty"), ("department", "Department"), ("semester", "Semester"),
                  ("academic year", "Academic year")], "State the faculty, department, semester and academic year.")

    coord = info.get("course coordinator")
    no_coord = coord is None or is_empty(coord[0])
    no_instr = not spec.instructors()
    if no_coord or no_instr:
        gaps = (["a course coordinator"] if no_coord else []) + (["an instructor"] if no_instr else [])
        out.append(draft("1.6", f"{CI}, row \"Course coordinator\"" if no_coord else "Instructors table",
                         _row_quote(coord[1]) if no_coord and coord else "(absent)",
                         "No " + " and no ".join(gaps) + " is named.",
                         "Name the course coordinator and at least one instructor.",
                         line=coord[1].no if no_coord and coord else None))

    multi("1.7", [("degree level", "Degree level"), ("related curricula", "Related curricula"),
                  ("course status", "Course status"), ("course description", "Course description")],
          "State the degree level, related curricula, course status and course description.")

    CLOS = "Course learning outcomes"
    if not spec.clos:
        out.append(draft("2.1", f"{CLOS} table", _row_quote(spec.clo_table.header_line),
                         "No CLO is listed.", "List at least one course learning outcome.",
                         line=spec.clo_table.header_line.no))

    rp = spec.sec("program learning outcomes related to the course")
    if rp is None or not plo_ids(" ".join(b.text for b in rp.body)):
        quote = "(absent)" if rp is None else ("-" if rp.is_dash() else rp.body[0].text.strip())
        out.append(draft("2.3", "Program learning outcomes related to the course", quote,
                         "The related-PLO section lists no PLO ID.",
                         "List the PLO IDs from plo-catalog.md that this course's CLOs map to.",
                         line=(rp.dash_line().no if rp else None)))
    for c in spec.clos:
        if not c.plos and is_empty(c.plo_cell):
            out.append(draft("2.4", f"{CLOS}, row \"{c.id}\"", _row_quote(c.line),
                             f"{c.id} maps to no PLO (cell is '{c.plo_cell or ''}', no reason stated).",
                             f"Map {c.id} to at least one PLO ID from plo-catalog.md.", line=c.line.no))

    content = spec.sec("content")
    topics = [(ln, cells) for t in (content.tables if content else []) for ln, cells in t.rows
              if len(cells) > 1 and not is_empty(cells[1])]
    if not topics:
        fix31 = "List the content topics week by week, with the CLOs each covers."
        if content is None or content.is_dash():
            _section_rule(spec, out, "3.1", "content", "Content", fix31)
        else:
            hdr = content.tables[0].header_line if content.tables else content.line
            out.append(draft("3.1", "Content section", _row_quote(hdr), "No content topic is listed.",
                             fix31, line=hdr.no))
    else:                                         # precedence 2: 3.2 only when 3.1 passes
        covered = {c for _, cells in topics for c in clo_ids(" ".join(cells[2:]))}
        for c in spec.clos:
            if c.id not in covered:
                out.append(draft("3.2", f"{CLOS}, row \"{c.id}\"", _row_quote(c.line),
                                 f"No content topic lists {c.id}.",
                                 f"Add {c.id} to the topics that teach it.", line=c.line.no))
    _section_rule(spec, out, "3.3", "teaching media", "Teaching media", "List the teaching media used.")
    _section_rule(spec, out, "3.4", "communication channels / lms", "Communication channels / LMS",
                  "State the LMS or communication channel students use.")

    A = "Assessment table"
    weighted = [m for m in spec.methods if m.weight is not None]
    if not weighted:
        out.append(draft("4.1", A, _row_quote(spec.assessment_table.header_line),
                         "No assessment method is listed with a weight.",
                         "List each assessment method with its percentage.",
                         line=spec.assessment_table.header_line.no))
    for m in spec.methods:
        if m.weight is None or m.weight < 0:
            out.append(draft("4.2", f"{A}, row \"{m.name}\"", _row_quote(m.line),
                             f"Weight '{m.weight_cell}' of {m.name} is not a non-negative number.",
                             "Give the method a numeric weight of 0 or more.", line=m.line.no))
    if weighted:
        w = weight_report(spec)
        if abs(w["sum"] - 100) > 1e-9:
            gap = f"short by {fmt(-w['delta_from_100'])}" if w["sum"] < 100 else f"over by {fmt(w['delta_from_100'])}"
            bonus = f" Bonus rows outside the sum: {', '.join(w['bonus_excluded'])}." if w["bonus_excluded"] else ""
            out.append(draft("4.3", A, _row_quote(spec.assessment_table.header_line),
                             f"Assessment weights sum to {fmt(w['sum'])} ({w['arithmetic']}), not 100: {gap}.{bonus}",
                             "Adjust the method weights, or add the missing method to the table, so they sum to exactly 100.",
                             line=spec.assessment_table.header_line.no))
    for m in spec.methods:
        if not is_exempt(m) and not m.clos and not is_bonus(m):
            out.append(draft("4.4", f"{A}, row \"{m.name}\"", _row_quote(m.line),
                             f"{m.name} maps to no CLO.", f"List the CLOs that {m.name} assesses.",
                             line=m.line.no))
    assessed = {c for m in spec.methods for c in m.clos}
    for c in spec.clos:
        if c.id not in assessed:
            out.append(draft("4.5", f"{CLOS}, row \"{c.id}\"", _row_quote(c.line),
                             f"No assessment method lists {c.id}.",
                             f"Assess {c.id} with at least one method in the assessment table.", line=c.line.no))
    for m in spec.methods:
        if not is_exempt(m) and not is_bonus(m) and m.level is None:
            out.append(draft("4.6", f"{A}, row \"{m.name}\"", _row_quote(m.line),
                             f"{m.name} states no measurement level ('{m.level_cell}').",
                             f"State the Bloom level {m.name} measures, e.g. Bloom's taxonomy (Apply).",
                             line=m.line.no))
    for s in splits(spec):
        others = [o for o in splits(spec) if o["method"] == s["method"] and o["line"] < s["line"]]
        if s["weight"] is not None and abs(s["sum"] - s["weight"]) > 1e-9:
            out.append(draft("4.10", f"Assessment note, split of \"{s['method']}\"", s["quote"],
                             f"The sub-parts of {s['method']} sum to {fmt(s['sum'])}, not its weight {fmt(s['weight'])}.",
                             f"Make the sub-parts of {s['method']} add up to {fmt(s['weight'])}.", line=s["line"]))
        elif others and any(o["parts"] != s["parts"] for o in others):
            o = others[0]
            diff = sorted(set(o["parts"].items()) ^ set(s["parts"].items()))
            out.append(draft("4.10", f"Assessment note, second statement of the {s['method']} split", s["quote"],
                             f"Two statements of the {s['method']} split disagree (line {o['line']} vs line {s['line']}): "
                             + ", ".join(f"{k} {fmt(v)}" for k, v in diff) + ".",
                             f"State the {s['method']} split once, or make both statements list the same parts and points.",
                             line=s["line"]))

    G = "Grading table"
    grades = {g.upper(): (v, ln) for g, v, ln in spec.grades()}
    need = ["A", "B+", "B", "C+", "C", "D+", "D"]
    gaps = [g for g in need if g not in grades or grades[g][0] is None]
    if gaps:
        out.append(draft("5.1", G, _row_quote(spec.grade_table.header_line),
                         "No threshold for grade(s): " + ", ".join(gaps) + ".",
                         "List a threshold for every grade from A to D; F is the remainder.",
                         line=spec.grade_table.header_line.no))
    present = [(g, grades[g][0], grades[g][1]) for g in need if g in grades and grades[g][0] is not None]
    for (g1, v1, _), (g2, v2, ln2) in zip(present, present[1:]):
        if not v1 > v2:
            out.append(draft("5.2", f"{G}, row \"{g2}\"", _row_quote(ln2),
                             f"Threshold for {g2} ({fmt(v2)}) is not below {g1} ({fmt(v1)}).",
                             "Make thresholds fall strictly from A to D.", line=ln2.no))
    for g, v, ln in present:
        if not 0 <= v <= 100:
            out.append(draft("5.2", f"{G}, row \"{g}\"", _row_quote(ln), f"Threshold {fmt(v)} for {g} is outside 0-100.",
                             "Keep every threshold between 0 and 100.", line=ln.no))

    note = spec.sec("assessment note")
    nq = ("-" if note.is_dash() else note.body[0].text.strip()) if note else "(absent)"
    nline = (note.dash_line().no if note.is_dash() else note.line.no) if note else None
    NOTE = "Assessment note"
    if not _policy_present(spec, r"\blate\b|deadline"):
        out.append(draft("6.1", NOTE, nq, "No deadline or late-submission policy anywhere in the document.",
                         "State the deadline and late-submission policy in the assessment note.", line=nline))
    if not _policy_present(spec, r"integrity|plagiar"):
        out.append(draft("6.2", NOTE, nq, "No academic-integrity or plagiarism statement anywhere in the document.",
                         "Add an academic-integrity and plagiarism statement to the assessment note.", line=nline))
    if not _policy_present(spec, r"\bAI\b"):
        out.append(draft("6.3", NOTE, nq, "No statement on the use of AI tools anywhere in the document.",
                         "State what use of AI tools is allowed in this course.", line=nline))
    graded = any(is_exempt(m) and (m.weight or 0) > 0 for m in spec.methods)
    required = _policy_present(spec, r"attendance[^.]*\b(required|mandatory|compulsory)")
    if (graded or required) and not _policy_present(spec, r"attendance"):
        out.append(draft("6.4", NOTE, nq, "Attendance is graded or required but no attendance policy is stated.",
                         "State the attendance policy in the assessment note.", line=nline))

    _section_rule(spec, out, "7.1", "reading list", "Reading list", "Give a reading list.")
    TE = "Teaching evaluation"
    _field_rule(spec, out, "7.2", "teaching evaluation", TE, "evaluation channel", "Evaluation channel",
                "State the channel students use to evaluate the teaching.")
    _field_rule(spec, out, "7.3", "teaching evaluation", TE, "changes after the previous evaluation",
                "Changes after the previous evaluation",
                "State what changed after the previous evaluation, or 'first offering'.")
    _field_rule(spec, out, "7.4", "course quality control", "Course quality control",
                "response to student complaints", "Response to student complaints",
                "State how student complaints are handled.")

    ai = spec.sec("ai-related learning")
    if ai is not None:
        kv = ai.kv()
        get = lambda k: kv.get(k, ("", None))[0]  # noqa: E731
        topics, hours = get("ai topics taught"), get("total hours")
        try:
            h = float(re.findall(r"\d+(?:\.\d+)?", hours)[0])
        except IndexError:
            h = None
        none_topics = is_empty(topics) or topics.strip().lower() in {"none", "no"}
        ok = (none_topics and h == 0) or (not none_topics and h and h > 0
                                          and not is_empty(get("learning strategy"))
                                          and not is_empty(get("assessment strategy")))
        if not ok:
            out.append(draft("7.5", "AI-related learning", _row_quote(ai.line),
                             "The AI-related learning section is incomplete: topics, hours and both strategies do not agree.",
                             "Either state no AI topics with 0 hours, or give the topics, hours and both strategies.",
                             line=ai.line.no))
    _section_rule(spec, out, "7.6", "sdg alignment", "SDG alignment", "State the SDG goals this course aligns with.")
    return out


# =================================================== curriculum-auditor rules
def check_bloom(spec: Spec, overrides: dict | None = None) -> list[dict]:
    """2.2, 4.7, 4.8, 4.9 under precedence 3-6."""
    if f1_failed(spec):
        return []
    out = []
    levels = clo_levels(spec, overrides)
    CLOS, A = "Course learning outcomes", "Assessment table"
    for c in spec.clos:
        d = levels[c.id]
        if not d["classifiable"]:
            out.append(draft("2.2", f"{CLOS}, row \"{c.id}\"", c.line.text.strip(),
                             f"{c.id} has no verb naming something the student does; it reads as a teaching aim "
                             f"('{d['first_word']}' is not in bloom-taxonomy.md and has no clear synonym).",
                             f"Rewrite {c.id} as a student outcome with a classifiable verb, e.g. 'Explain ...' or 'Design ...'.",
                             standard_ref="bloom-taxonomy.md, 'Deriving a CLO's level' rule 4", line=c.line.no))

    def ref_for(m, top_clo):
        d = levels[top_clo]
        v = max(d["verbs"], key=lambda x: RANK[x["level"]]) if d["verbs"] else None
        how = "" if not v else (f"'{v['verb']}' = {v['level']}" + ("" if v["how"] == "dictionary"
                                else f" ({'by convention' if v['how'] == 'convention' else v['how']})"))
        return f"{BLOOM_REF}: {top_clo} {how}; method '{m.name}' stated at {m.level}"

    failed_47 = set()
    for m in spec.methods:
        skip = m.level is None or (not is_exempt(m) and not m.clos)        # 4.4 / 4.6 failures
        known = [c for c in m.clos if c in levels and levels[c]["level"]]
        if skip or not known:
            continue
        top = max(known, key=lambda c: RANK[levels[c]["level"]])
        if RANK[m.level] > RANK[levels[top]["level"]]:
            failed_47.add(m.name)
            out.append(draft("4.7", f"{A}, row \"{m.name}\"", m.line.text.strip(),
                             f"{m.name} is stated at {m.level}, above the highest level of the CLOs it assesses "
                             f"({', '.join(f'{c} {levels[c]['level']}' for c in known)}).",
                             f"Lower {m.name}'s measurement level to {levels[top]['level']} or below, "
                             "or map it to a CLO that asks for the higher level.",
                             standard_ref=ref_for(m, top), line=m.line.no))
    for m in spec.methods:                                                  # precedence 6
        if m.level is None or m.name in failed_47 or (not is_exempt(m) and not m.clos):
            continue
        typ, top = method_type(m)
        if is_exempt(m) or top is None:
            msg = f"{m.name} is an attendance/participation row and can evidence no cognitive level, but states {m.level}."
            fix = f"Remove the measurement level from {m.name}, or replace it with a method that evidences {m.level}."
        elif RANK[m.level] > RANK[top]:
            msg = f"{m.name} is a {typ.lower()} method, which evidences at most {top}, but it states {m.level}."
            fix = f"Measure {m.level} with a deliverable that can evidence it (bloom-taxonomy.md, Method types), or lower the level."
        else:
            continue
        out.append(draft("4.9", f"{A}, row \"{m.name}\"", m.line.text.strip(), msg, fix,
                         standard_ref=f"{BLOOM_REF}; bloom-taxonomy.md, Method types: {typ}", line=m.line.no))
    for c in spec.clos:
        d = levels[c.id]
        mine = [m for m in spec.methods if c.id in m.clos]
        stated = [m for m in mine if m.level]
        if not d["level"] or not mine or not stated:                        # precedence 4, 5
            continue
        best = max(stated, key=lambda m: RANK[m.level])
        if RANK[best.level] < RANK[d["level"]]:
            v = max(d["verbs"], key=lambda x: RANK[x["level"]])
            out.append(draft("4.8", f"{CLOS}, row \"{c.id}\"", c.line.text.strip(),
                             f"{c.id} derives to {d['level']} ('{v['verb']}'), but its methods "
                             f"({', '.join(f'{m.name} {m.level}' for m in stated)}) measure it at {best.level} at most.",
                             f"Assess {c.id} at {d['level']} with at least one method, e.g. a project or report deliverable.",
                             standard_ref=f"{BLOOM_REF}: '{v['verb']}' = {d['level']}", line=c.line.no))
    return out


def check_plo(spec: Spec) -> list[dict]:
    """2.5 and 2.6 (2.7 is advisory judgment: add_finding)."""
    if f1_failed(spec):
        return []
    out, cat = [], ds.plo_catalog()
    RP, CLOS = "Program learning outcomes related to the course", "Course learning outcomes"
    section_lines = spec.related_plo_lines()
    for ln in section_lines:
        for p in plo_ids(ln.text):
            if p not in cat:
                out.append(draft("2.5", RP, ln.text.strip(), f"PLO ID '{p}' does not exist in plo-catalog.md.",
                                 f"Replace '{p}' with a PLO ID from plo-catalog.md.",
                                 standard_ref=f"plo-catalog.md: PLO ID '{p}' does not exist", line=ln.no))
    for c in spec.clos:
        for p in c.plos:
            if p not in cat:
                out.append(draft("2.5", f"{CLOS}, row \"{c.id}\"", c.line.text.strip(),
                                 f"{c.id} cites PLO ID '{p}', which does not exist in plo-catalog.md.",
                                 f"Replace '{p}' with a PLO ID from plo-catalog.md.",
                                 standard_ref=f"plo-catalog.md: PLO ID '{p}' does not exist", line=c.line.no))
    listed = {p for ln in section_lines for p in plo_ids(ln.text)}
    p23_ok = bool(listed)
    p24_ok = all(c.plos or not is_empty(c.plo_cell) for c in spec.clos)
    if p23_ok and p24_ok:                                                   # precedence 2
        used = {}
        for c in spec.clos:
            for p in c.plos:
                used.setdefault(p, c)
        for p, c in used.items():
            if p not in listed:
                out.append(draft("2.6", f"{RP}: {p} is missing (it is used on {c.id})", c.line.text.strip(),
                                 f"The CLOs use {p}, but the related-PLO section does not list it.",
                                 f"Add {p} to the related-PLO section, or remove it from {c.id}.",
                                 standard_ref="checklist.md 2.6; plo-catalog.md", line=c.line.no))
        for ln in section_lines:
            for p in plo_ids(ln.text):
                if p not in used:
                    out.append(draft("2.6", f"{CLOS}: no CLO maps to {p}", ln.text.strip(),
                                     f"The related-PLO section lists {p}, but no CLO maps to it.",
                                     f"Map a CLO to {p}, or remove {p} from the related-PLO section.",
                                     standard_ref="checklist.md 2.6; plo-catalog.md", line=ln.no))
    return out


def plo_coverage(specs: list[Spec], open_blocker: dict[str, bool]) -> list[dict]:
    """Batch rollup per plo-mapping-standard: courses with/without an open blocker per PLO."""
    rows = []
    for pid, meta in ds.plo_catalog().items():
        clean, blocked = [], []
        for s in specs:
            if f1_failed(s) or not any(pid in c.plos for c in s.clos):
                continue
            (blocked if open_blocker.get(s.course_code) else clean).append(s.course_code)
        status = "covered" if clean else "claimed, not yet approved" if blocked else "gap"
        rows.append({"plo": pid, "wa": meta["wa"], "clean": sorted(clean), "blocked": sorted(blocked),
                     "status": status})
    return rows


# ===================================================================== verdict
def compute_verdict(findings: list[dict]) -> dict:
    """The entire verdict logic (committee-review-format policy table)."""
    openf = [f for f in findings if str(f.get("status", "open")).strip().lower() != "resolved"]
    count = {sev: sum(1 for f in openf if str(f.get("severity")).lower() == sev)
             for sev in ("blocker", "major", "minor")}
    verdict = "RETURN" if count["blocker"] else "REVISE" if count["major"] else "APPROVE"
    return {"verdict": verdict, "open_counts": count,
            "resolved_count": len(findings) - len(openf),
            "open_blocker_ids": [f["id"] for f in openf if str(f.get("severity")).lower() == "blocker"]}
