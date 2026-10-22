"""Read evaluation/<code>.md (the plugin's ground truth) and score a review against it.

Only the evaluator uses this module. No tool exposes it, and data_store.resolve_spec
refuses evaluation/, so an agent stage can never read the answers.

Scoring follows evaluation/README.md: a reported finding hits an expected one when the
rule matches (or is the expected finding's "same defect under another rule") and the
location line or the verbatim quote matches; extra matches are duplicates; a match with a
tolerated entry counts neither way; everything else is a false positive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Expected:
    gid: str
    rule: str
    severity: str
    owner: str
    line: int | None
    quote: str
    alt_rules: list[str] = field(default_factory=list)


@dataclass
class Truth:
    code: str
    verdict: str
    counts: dict
    weight_sum: float | None
    expected: list[Expected]
    tolerated_rules: list[str]
    traps: list[str]


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().strip("`").strip())


def _line(text: str) -> int | None:
    m = re.search(r"\(line (\d+)\)", text or "")
    return int(m[1]) if m else None


def load(path: Path) -> Truth:
    t = path.read_text(encoding="utf-8")
    verdict = re.search(r"Expected verdict:\s*\*\*(\w+)\*\*", t)[1]
    m = re.search(r"Open findings:\s*(\d+) blocker\s*·\s*(\d+) major\s*·\s*(\d+) minor", t)
    counts = {"blocker": int(m[1]), "major": int(m[2]), "minor": int(m[3])}
    w = re.search(r"Assessment weights:[^\n=]*=\s*([\d.]+)", t)
    expected = []
    for b in re.split(r"^### ", t.split("## Expected findings", 1)[1].split("## Tolerated", 1)[0],
                      flags=re.M)[1:]:
        h = re.match(r"(G\d+)\s*·\s*Rule\s*(\S+)\s*·\s*(\w+)\s*·\s*([\w-]+)", b)
        loc = re.search(r"- Location:\s*(.*)", b)
        quote = re.search(r"- Quote:\s*`(.*)`", b)
        alt = re.findall(r"a (\d+\.\d+|F\.\d+) report", re.search(r"- Same defect[^\n]*", b)[0]) \
            if "Same defect" in b else []
        expected.append(Expected(h[1], h[2], h[3].lower(), h[4], _line(loc[1] if loc else ""),
                                 _norm(quote[1]) if quote else "", alt))
    tol = re.findall(r"^\|\s*(\d+\.\d+|F\.\d+) \(", t.split("## Tolerated findings", 1)[1].split("## Must not", 1)[0],
                     flags=re.M)
    traps = [r.split("|")[1].strip() for r in t.split("## Must not flag", 1)[1].splitlines()
             if r.startswith("|") and not r.startswith("|---") and "Trap" not in r] if "## Must not flag" in t else []
    return Truth(path.stem, verdict, counts, float(w[1]) if w else None, expected, tol, traps)


def load_all(evaluation_dir: Path) -> dict[str, Truth]:
    return {p.stem: load(p) for p in sorted(evaluation_dir.glob("*.md")) if p.stem != "README"}


def score(truth: Truth, findings: list[dict], verdict: str) -> dict:
    """Per-course score against evaluation/README.md 'Scoring a take'."""
    hits, dupes, tolerated, fps = {}, 0, 0, []
    rule_ok = sev_ok = 0
    for f in findings:
        if str(f.get("status", "open")).lower() == "resolved":
            continue
        line, quote, rule = _line(f.get("section", "")), _norm(f.get("quote", "")), f.get("checklist_rule")
        match = next((e for e in truth.expected
                      if rule in [e.rule, *e.alt_rules]
                      and ((line is not None and line == e.line) or (quote and quote == e.quote))), None)
        if match is None:
            if rule in truth.tolerated_rules:
                tolerated += 1
            else:
                fps.append(f"{rule} {f.get('section')}")
        elif match.gid in hits:
            dupes += 1
        else:
            hits[match.gid] = f
            rule_ok += rule == match.rule
            sev_ok += str(f.get("severity")).lower() == match.severity
    misses = [f"{e.gid} {e.rule} line {e.line}" for e in truth.expected if e.gid not in hits]
    return {"course": truth.code, "verdict_ok": verdict == truth.verdict, "verdict": verdict,
            "expected_verdict": truth.verdict, "hits": len(hits), "expected": len(truth.expected),
            "misses": misses, "duplicates": dupes, "tolerated": tolerated, "false_positives": fps,
            "rule_accuracy": (rule_ok, len(hits)), "severity_accuracy": (sev_ok, len(hits))}
