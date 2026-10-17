"""Deterministic parser for the course_specification.md template.

Pure functions, no model involved. Every extracted item keeps the verbatim source
line (`raw`) so findings can quote the document exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

BLOOM_LEVELS = ("Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create")
POLICY_KEYS = {  # policy -> keywords found in the bullet label
    "attendance": ("attendance",),
    "deadlines": ("deadline", "late"),
    "academic_integrity": ("academic integrity",),
    "plagiarism": ("plagiarism", "citation"),
    "ai_tools": ("ai tool", "critical use"),
}
_EMPTY = {"", "-", "—", "–", "n/a", "na", "none", "tbd"}


@dataclass
class CLO:
    id: str
    description: str
    bloom: str
    plos: list[str]
    raw: str


@dataclass
class Assessment:
    component: str
    weight: float | None
    clos: list[str]
    raw: str


@dataclass
class Spec:
    path: str
    course_code: str | None = None
    course_name: str | None = None
    clos: list[CLO] = field(default_factory=list)
    assessments: list[Assessment] = field(default_factory=list)
    stated_total: float | None = None
    rubric_items: int = 0
    policies: dict[str, str] = field(default_factory=dict)  # policy -> verbatim bullet
    sections_found: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _tables(text: str):
    """Yield (header_cells, [(raw_line, cells)]) for each markdown table."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if (lines[i].lstrip().startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1])):
            header = [h.lower() for h in _cells(lines[i])]
            rows, i = [], i + 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append((lines[i].strip(), _cells(lines[i])))
                i += 1
            yield header, rows
        else:
            i += 1


def _col(header: list[str], name: str) -> int | None:
    for k, h in enumerate(header):
        if name in h:
            return k
    return None


def _get(cells: list[str], idx: int | None) -> str:
    return cells[idx] if idx is not None and idx < len(cells) else ""


def split_ids(cell: str) -> list[str]:
    """'CLO1, CLO2' / 'PLO1; PLO3' -> list. '-', 'n/a', '' -> []"""
    if cell.strip().lower() in _EMPTY:
        return []
    return [t for t in re.split(r"[,;/\s]+", cell.strip()) if t]


def parse_spec(text: str, path: str = "") -> Spec:
    s = Spec(path=path)
    if m := re.search(r"\*\*Course Code:\*\*[ \t]*(.*)", text):
        s.course_code = m[1].strip() or None
    if m := re.search(r"\*\*Course Name:\*\*[ \t]*(.*)", text):
        s.course_name = m[1].strip() or None
    s.sections_found = re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)

    for header, rows in _tables(text):
        if _col(header, "clo") == 0 and _col(header, "bloom") is not None:
            d, b, p = _col(header, "description"), _col(header, "bloom"), _col(header, "plo")
            for raw, c in rows:
                s.clos.append(CLO(id=c[0], description=_get(c, d), bloom=_get(c, b),
                                  plos=split_ids(_get(c, p)), raw=raw))
        elif _col(header, "component") is not None and _col(header, "weight") is not None:
            k, w, m = _col(header, "component"), _col(header, "weight"), _col(header, "clo")
            for raw, c in rows:
                try:
                    weight = float(_get(c, w).replace("%", "").strip())
                except ValueError:
                    weight = None
                s.assessments.append(Assessment(component=_get(c, k), weight=weight,
                                                clos=split_ids(_get(c, m)), raw=raw))

    if m := re.search(r"\*\*Total:\s*([\d.]+)", text):
        s.stated_total = float(m[1])

    if m := re.search(r"^#{2,4}[ \t]*Scoring Criteria[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", text,
                      re.MULTILINE | re.DOTALL | re.IGNORECASE):
        s.rubric_items = len(re.findall(r"^\s*[-*]\s+\S", m[1], re.MULTILINE))

    for m in re.finditer(r"^\s*[-*]\s+\*\*([^*:]+):?\*\*:?[ \t]*(.*)$", text, re.MULTILINE):
        label = m[1].strip().lower()
        for key, words in POLICY_KEYS.items():
            if any(w in label for w in words) and m[2].strip():
                s.policies.setdefault(key, m[0].strip())
    return s
