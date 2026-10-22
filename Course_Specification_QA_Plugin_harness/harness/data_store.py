"""Filesystem layer: the plugin's courses/ and references/, and the reports/ output folder.

The plugin root is the parent of this harness folder. The rulebook is read from the
plugin's own files at run time, never copied into code:

  references/checklist.md       rules: ID, check, severity, owner
  references/bloom-taxonomy.md  verb dictionary, convention verbs, method types
  references/plo-catalog.md     valid PLO IDs and their WA attributes
  hooks/validate_findings.py    the plugin's findings.json validator, imported and reused

Output goes to this harness's own reports/ by default, so a harness run never touches the
plugin's reports/; pass ``reports=<plugin>/reports`` to write where the plugin writes.
Tests call ``configure(tmp)`` to point everything at a scratch copy.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
_root = HARNESS_ROOT.parent
_reports = HARNESS_ROOT / "reports"
_cache: dict = {}

LEVELS = ("Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create")
NOT_REVIEWABLE = ("evaluation", "reports")   # commands/review-spec.md: never review these


def configure(root: str | Path | None = None, reports: str | Path | None = None) -> None:
    """Point the tools at a plugin root and a reports folder (default: <root>/reports)."""
    global _root, _reports
    if root is not None:
        _root = Path(root).resolve()
    _reports = Path(reports).resolve() if reports else _root / "reports"
    _cache.clear()


def root() -> Path:
    return _root


def courses_dir() -> Path:
    return _root / "courses"


def reports_dir() -> Path:
    return _reports


def evaluation_dir() -> Path:
    return _root / "evaluation"


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(_root)).replace("\\", "/")
    except ValueError:
        return str(p)


def resolve_spec(path: str) -> Path:
    """Resolve a spec path. Only .md files under the plugin root, outside evaluation/ and reports/."""
    p = Path(path)
    p = (p if p.is_absolute() else _root / p).resolve()
    if _root not in p.parents:
        raise PermissionError(f"{path}: outside the plugin root")
    if p.relative_to(_root).parts[0] in NOT_REVIEWABLE or _reports in p.parents:
        raise PermissionError(f"{path}: evaluation/ (ground truth) and reports/ are never reviewed")
    if p.suffix.lower() != ".md":
        raise PermissionError(f"{path}: only Markdown specs are supported (PDF needs text extraction first)")
    if not p.is_file():
        raise FileNotFoundError(f"{path}: no such file. Use list_course_specs to see valid paths")
    return p


def list_specs() -> list[str]:
    return sorted(rel(p) for p in courses_dir().glob("*.md"))


# ------------------------------------------------------------------- rulebook
def _ref(name: str) -> Path:
    return _root / "references" / name


def _cached(key: str, path: Path, build):
    stamp = (key, str(path), path.stat().st_mtime_ns if path.exists() else None)
    if stamp not in _cache:
        _cache[stamp] = build()
    return _cache[stamp]


def checklist_path() -> Path:
    return _ref("checklist.md")


def rulebook_sha256() -> str | None:
    try:
        return hashlib.sha256(checklist_path().read_bytes()).hexdigest()
    except OSError:
        return None


def checklist() -> dict[str, dict]:
    """Rule ID -> {check, severity, owner}, from the rule table in checklist.md."""
    def build():
        rules = {}
        for line in checklist_path().read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not (s.startswith("|") and s.endswith("|")):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 4 and re.match(r"^(?:[A-Z]\.\d+|\d+\.\d+)$", cells[0]):
                rules[cells[0]] = {"check": " | ".join(cells[1:-2]),
                                   "severity": cells[-2].lower(), "owner": cells[-1].lower()}
        if not rules:
            raise RuntimeError(f"{checklist_path()} has no rule rows")
        return rules
    return _cached("checklist", checklist_path(), build)


def validator():
    """The plugin's hooks/validate_findings.py, imported as a module (single source of truth)."""
    path = _root / "hooks" / "validate_findings.py"

    def build():
        spec = importlib.util.spec_from_file_location("course_spec_qa_validate_findings", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return _cached("validator", path, build)


def bloom() -> dict:
    """Verb lexicon and method types parsed from bloom-taxonomy.md.

    {"verbs": {verb: (level, how)}, "method_types": [(type, [example names], max_level|None)]}
    how = "dictionary" (Anderson & Krathwohl) or "convention" (professional-practice verbs).
    """
    path = _ref("bloom-taxonomy.md")

    def build():
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"```\n(.*?)```", text, re.DOTALL)
        verbs: dict[str, tuple[str, str]] = {}
        for i, block in enumerate(blocks[:2]):           # 1st: dictionary, 2nd: convention
            for m in re.finditer(r"^(\w+):\s*(.+)$", block, re.MULTILINE):
                level = m[1].capitalize()
                for v in m[2].split(","):
                    verbs.setdefault(v.strip().lower(), (level, "dictionary" if i == 0 else "convention"))
        types = []
        sec = text.split("## Method types", 1)[-1]
        for line in sec.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] not in ("Method type",) and not set(cells[0]) <= set("-: "):
                lv = next((l for l in LEVELS if re.search(rf"\b{l}\b", cells[2])), None)
                examples = [e.strip().lower() for e in cells[1].split(",") if e.strip()]
                types.append((cells[0], examples, None if cells[2].lower().startswith("none") else lv))
        return {"verbs": verbs, "method_types": types}
    return _cached("bloom", path, build)


def plo_catalog() -> dict[str, dict]:
    """PLO ID -> {statement, wa}, from the table in plo-catalog.md."""
    path = _ref("plo-catalog.md")

    def build():
        out = {}
        for m in re.finditer(r"^\|\s*(PLO\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
                             path.read_text(encoding="utf-8"), re.MULTILINE):
            out[m[1]] = {"statement": m[2], "wa": m[3]}
        return out
    return _cached("plo", path, build)


# ------------------------------------------------------------------- findings
def course_dir(course_code: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,32}", course_code or ""):
        raise ValueError(f"bad course code {course_code!r}")
    return reports_dir() / course_code


def findings_path(course_code: str) -> Path:
    return course_dir(course_code) / "findings.json"


def load_findings(course_code: str) -> list[dict]:
    p = findings_path(course_code)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []


def save_findings(course_code: str, findings: list[dict]) -> Path:
    """Write findings.json only if the plugin's validate_findings.py would allow it."""
    v = validator()
    rules = v.load_rules(str(checklist_path()))
    problems = v.check_findings(findings, rules)
    p = findings_path(course_code)
    if p.is_file():
        old, _ = v.parse_findings(p.read_text(encoding="utf-8"))
        if old is not None:
            problems += v.check_append_only(old, findings)
    if problems:
        raise ValueError("Blocked by validate_findings.py: " + "; ".join(problems[:5]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def clear_course(course_code: str) -> None:
    """The README's 'clear reports/<course_code>/ before reviewing again', done by the orchestrator."""
    d = course_dir(course_code)
    if d.is_dir():
        shutil.rmtree(d)


def load_json(course_code: str, name: str, default):
    p = course_dir(course_code) / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def save_json(course_code: str, name: str, data) -> None:
    p = course_dir(course_code) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    new = not path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if new:
            w.writeheader()
        w.writerows(rows)
