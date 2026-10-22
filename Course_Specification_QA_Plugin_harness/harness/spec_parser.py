"""Deterministic parser for the official CU course-specification form (English rendering).

Follows references/course-spec-template.md. Every extracted item keeps its 1-based line
number and the verbatim line, so a finding can point at the row and quote it exactly.
Sections are keyed by their English heading, lowercased, without the Thai in brackets:
"## Assessment (การประเมินผลการเรียน)" -> "assessment".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data_store import LEVELS

EMPTY = {"", "-", "—", "–"}
PLO_RE = re.compile(r"\bPLO\s?\d+\b", re.IGNORECASE)
CLO_RE = re.compile(r"\bCLO\s?\d+\b", re.IGNORECASE)


def is_empty(value: str | None) -> bool:
    return value is None or value.strip() in EMPTY


def english(label: str) -> str:
    """'Course code (รหัสรายวิชา)' -> 'course code'."""
    return re.sub(r"\s*\([^)]*[^\x00-\x7F][^)]*\)", "", label).strip().lower()


def plo_ids(text: str) -> list[str]:
    return [re.sub(r"\s", "", m).upper() for m in PLO_RE.findall(text or "")]


def clo_ids(text: str) -> list[str]:
    return [re.sub(r"\s", "", m).upper() for m in CLO_RE.findall(text or "")]


@dataclass
class Line:
    no: int
    text: str


@dataclass
class Table:
    header: list[str]               # lowercased English header cells
    header_line: Line
    rows: list[tuple[Line, list[str]]]

    def col(self, *names: str) -> int | None:
        for k, h in enumerate(self.header):
            if any(n in h for n in names):
                return k
        return None


@dataclass
class Section:
    title: str                      # heading as printed
    key: str                        # English, lowercased
    line: Line
    level: int                      # 2 for ##, 3 for ###
    body: list[Line] = field(default_factory=list)      # non-blank, non-table lines
    tables: list[Table] = field(default_factory=list)

    def is_dash(self) -> bool:
        """Section printed as a lone '-' (or with nothing at all)."""
        return not self.tables and all(is_empty(b.text.lstrip("- ").strip()) or b.text.strip() == "-"
                                       for b in self.body)

    def dash_line(self) -> Line:
        return next((b for b in self.body if b.text.strip() == "-"), self.line)

    def kv(self) -> dict[str, tuple[str, Line]]:
        """Field | Value tables -> {english field: (value, line)}."""
        out = {}
        for t in self.tables:
            if t.header[:2] == ["field", "value"]:
                for ln, cells in t.rows:
                    if len(cells) >= 2:
                        out[english(cells[0])] = (cells[1], ln)
        return out


@dataclass
class CLO:
    id: str
    text: str
    plo_cell: str
    plos: list[str]
    line: Line


@dataclass
class Method:
    name: str
    level_cell: str
    level: str | None               # Bloom level named in the cell, if any
    clo_cell: str
    clos: list[str]
    weight_cell: str
    weight: float | None
    line: Line


@dataclass
class Spec:
    path: str
    lines: list[str]
    sections: dict[str, Section]
    clo_table: Table | None
    assessment_table: Table | None
    grade_table: Table | None
    clos: list[CLO]
    methods: list[Method]

    # --------------------------------------------------------------- helpers
    def sec(self, key: str) -> Section | None:
        return self.sections.get(key)

    def info(self) -> dict[str, tuple[str, Line]]:
        s = self.sec("course information")
        return s.kv() if s else {}

    def field(self, section_key: str, name: str) -> tuple[str, Line] | None:
        s = self.sec(section_key)
        return s.kv().get(name) if s else None

    @property
    def course_code(self) -> str | None:
        v = self.info().get("course code")
        if v and not is_empty(v[0]):
            return v[0].strip()
        m = re.search(r"Course code:\s*([A-Za-z]{2,5}\s?\d{3,4})", "\n".join(self.lines))
        return m[1].replace(" ", "") if m else None

    @property
    def course_title(self) -> str | None:
        info = self.info()
        for k in ("course title, english", "course title, thai"):
            if k in info and not is_empty(info[k][0]):
                return info[k][0]
        m = re.search(r"Course (?:title|name)[^:\n]*:\s*(.+)", "\n".join(self.lines))
        if m:
            return m[1].strip()
        first = self.lines[0].lstrip("# ").strip() if self.lines else ""
        return first or None

    def instructors(self) -> list[tuple[str, Line]]:
        s = self.sec("instructors")
        out = []
        for t in (s.tables if s else []):
            k = t.col("instructor")
            for ln, cells in t.rows:
                if k is not None and k < len(cells) and not is_empty(cells[k]):
                    out.append((cells[k], ln))
        return out

    def related_plo_lines(self) -> list[Line]:
        s = self.sec("program learning outcomes related to the course")
        return [b for b in s.body] if s else []

    def assessment_note(self) -> list[Line]:
        s = self.sec("assessment note")
        return s.body if s else []

    def grades(self) -> list[tuple[str, float | None, Line]]:
        if not self.grade_table:
            return []
        g, t = self.grade_table.col("grade"), self.grade_table.col("threshold")
        out = []
        for ln, cells in self.grade_table.rows:
            m = re.search(r"-?\d+(?:\.\d+)?", cells[t]) if t is not None and t < len(cells) else None
            out.append((cells[g].strip(), float(m[0]) if m else None, ln))
        return out

    def text_outside(self, *excluded_keys: str) -> list[Line]:
        """Every line not inside the given sections (used by the 6.x presence checks)."""
        skip = set()
        for k in excluded_keys:
            s = self.sec(k)
            if s:
                end = min((o.line.no for o in self.sections.values() if o.line.no > s.line.no
                           and o.level <= s.level), default=len(self.lines) + 1)
                skip.update(range(s.line.no, end))
        return [Line(i, t) for i, t in enumerate(self.lines, 1) if i not in skip]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_spec(text: str, path: str = "") -> Spec:
    lines = text.splitlines()
    sections: dict[str, Section] = {}
    order: list[Section] = []
    cur: Section | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        m = re.match(r"^(#{2,3})\s+(.+?)\s*$", raw)
        if m:
            cur = Section(m[2], english(m[2]), Line(i + 1, raw), len(m[1]))
            sections.setdefault(cur.key, cur)
            order.append(cur)
            i += 1
            continue
        if (raw.lstrip().startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1])):
            t = Table([english(h) for h in _cells(raw)], Line(i + 1, raw), [])
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                t.rows.append((Line(i + 1, lines[i]), _cells(lines[i])))
                i += 1
            if cur is not None:
                cur.tables.append(t)
            continue
        if raw.strip() and cur is not None:
            cur.body.append(Line(i + 1, raw))
        i += 1

    all_tables = [t for s in order for t in s.tables]
    clo_table = next((t for t in all_tables if t.header and "clo" in t.header[0]
                      and t.col("plo") is not None), None)
    assessment_table = next((t for t in all_tables if t.col("level") is not None
                             and t.col("clo") is not None), None)
    grade_table = next((t for t in all_tables if t.col("grade") is not None
                        and t.col("threshold") is not None), None)

    clos = []
    if clo_table:
        o, p = clo_table.col("outcome", "description"), clo_table.col("plo")
        for ln, c in clo_table.rows:
            cell = c[p] if p is not None and p < len(c) else ""
            clos.append(CLO(c[0].upper().replace(" ", ""),
                            c[o] if o is not None and o < len(c) else "", cell, plo_ids(cell), ln))

    methods = []
    if assessment_table:
        t = assessment_table
        k, lv, cl, w = t.col("method"), t.col("level"), t.col("clo"), t.col("percent", "weight")
        for ln, c in t.rows:
            get = lambda j: c[j] if j is not None and j < len(c) else ""  # noqa: E731
            level = next((L for L in LEVELS if re.search(rf"\b{L}\b", get(lv), re.I)), None)
            try:
                weight = float(get(w).replace("%", "").replace(",", "").strip())
            except ValueError:
                weight = None
            methods.append(Method(get(k), get(lv), level, get(cl), clo_ids(get(cl)), get(w), weight, ln))

    return Spec(path, lines, sections, clo_table, assessment_table, grade_table, clos, methods)
