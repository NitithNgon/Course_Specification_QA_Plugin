"""Filesystem layer for the QA tools: plugin root, courses/, references/, reports/.

The plugin root is the parent of this harness folder, so the harness reads the same
courses/ and references/ the Claude Code plugin does. Output goes to this harness's
own reports/ by default, so a harness run never overwrites the plugin's pilot
evidence; pass ``reports=<plugin>/reports`` to write where the plugin writes.
Tests call ``configure(tmp)`` to point everything at a scratch copy.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
_root = HARNESS_ROOT.parent
_reports = HARNESS_ROOT / "reports"


def configure(root: str | Path | None = None, reports: str | Path | None = None) -> None:
    """Point the tools at a plugin root and a reports folder (default: <root>/reports)."""
    global _root, _reports
    if root is not None:
        _root = Path(root).resolve()
    _reports = Path(reports).resolve() if reports else _root / "reports"


def root() -> Path:
    return _root


def courses_dir() -> Path:
    return _root / "courses"


def reports_dir() -> Path:
    return _reports


def resolve_spec(path: str) -> Path:
    """Resolve a spec path; only files under the plugin root are readable."""
    p = Path(path)
    p = (p if p.is_absolute() else _root / p).resolve()
    if _root not in p.parents:
        raise PermissionError(f"{path}: outside the plugin root")
    if p.suffix.lower() != ".md" or "gold" in p.name.lower():
        # gold labels are for the evaluator only (see courses/gold-labels.json _readme)
        raise PermissionError(f"{path}: only course spec .md files are readable")
    if not p.is_file():
        raise FileNotFoundError(f"{path}: no such file. Use list_course_specs to see valid paths")
    return p


def list_specs() -> list[str]:
    return sorted(str(p.relative_to(_root)).replace("\\", "/")
                  for p in courses_dir().glob("*.md"))


# ---------------------------------------------------------------- references
def read_reference(name: str) -> str:
    return (_root / "references" / name).read_text(encoding="utf-8")


def plo_catalog() -> dict[str, str]:
    """PLO ID -> statement, parsed from references/plo-catalog.md."""
    out = {}
    for m in re.finditer(r"^\|\s*(PLO\d+)\s*\|\s*([^|]+?)\s*\|", read_reference("plo-catalog.md"),
                         re.MULTILINE):
        out[m[1]] = m[2]
    return out


# ------------------------------------------------------------------ findings
def findings_path(course_code: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,16}", course_code):
        raise ValueError(f"bad course code {course_code!r}")
    return reports_dir() / course_code / "findings.json"


def load_findings(course_code: str) -> list[dict]:
    p = findings_path(course_code)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []


def save_findings(course_code: str, findings: list[dict]) -> Path:
    p = findings_path(course_code)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def append_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    new = not path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new:
            w.writeheader()
        w.writerows(rows)
