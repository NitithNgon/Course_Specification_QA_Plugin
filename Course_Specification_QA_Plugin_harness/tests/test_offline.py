"""Offline tests: no Ollama needed. A FakeClient replays scripted tool calls.

    python -m unittest discover -s tests -v          (from Course_Specification_QA_Plugin_harness/)

Every test runs against a scratch copy of courses/, references/ and hooks/ (never evaluation/
or the real reports/). The ground truth is read by the tests only, as the evaluator.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import ChatResult, Harness, TOOLS, execute, tool_defs  # noqa: E402
from harness import data_store as ds, ground_truth as gt, pipeline, qa_rules  # noqa: E402
from harness.agent_loop import run_stage  # noqa: E402
from harness.qa_tools import _coverage  # noqa: E402
from harness.spec_parser import parse_spec  # noqa: E402

PLUGIN = ds.HARNESS_ROOT.parent
EVAL = PLUGIN / "evaluation"
RW = {"read", "write"}


class FakeClient:
    """Returns queued outputs in order. A list item is a list of (tool, args) calls; a str is the final
    text; an exception instance is raised (Ollama down, or a crash)."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def chat(self, model, messages, **kw):
        self.requests.append({"model": model, "messages": list(messages), **kw})
        out = self.outputs.pop(0)
        if isinstance(out, BaseException):
            raise out
        if isinstance(out, list):
            calls = [{"function": {"name": n, "arguments": a}} for n, a in out]
            return ChatResult(model=model, content="", tool_calls=calls,
                              message={"role": "assistant", "content": "", "tool_calls": calls}, wall_s=0.01)
        return ChatResult(model=model, content=out, message={"role": "assistant", "content": out}, wall_s=0.01)


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qa_test_"))
        for d in ("courses", "references", "hooks"):
            shutil.copytree(PLUGIN / d, self.tmp / d, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        ds.configure(self.tmp)

    def tearDown(self):
        ds.configure(PLUGIN, reports=ds.HARNESS_ROOT / "reports")
        shutil.rmtree(self.tmp, ignore_errors=True)

    def harness(self, outputs=()):
        return Harness(client=FakeClient(outputs), log_file=self.tmp / "calls.jsonl")

    def call(self, name, args, allowed=frozenset({"read"})):
        return execute({"function": {"name": name, "arguments": args}}, allowed=set(allowed))

    def spec(self, code):
        return parse_spec((self.tmp / "courses" / f"{code}.md").read_text("utf-8"))


# --------------------------------------------------------- rulebook read at run time
class TestRulebook(Sandbox):
    def test_checklist_rows(self):
        rules = ds.checklist()
        self.assertEqual(len(rules), 41)
        sev = [r["severity"] for r in rules.values()]
        self.assertEqual((sev.count("blocker"), sev.count("major"), sev.count("minor")), (10, 11, 20))
        self.assertEqual(rules["4.7"]["owner"], "curriculum-auditor")
        self.assertEqual(rules["F.1"]["owner"], "course-reviewer")

    def test_bloom_and_catalog(self):
        b = ds.bloom()
        self.assertEqual(b["verbs"]["select"], ("Analyze", "dictionary"))
        self.assertEqual(b["verbs"]["function"], ("Apply", "convention"))
        self.assertEqual(len(b["method_types"]), 7)
        self.assertEqual(len(ds.plo_catalog()), 11)

    def test_checklist_edit_takes_effect(self):
        p = self.tmp / "references" / "checklist.md"
        p.write_text(p.read_text("utf-8").replace("| 7.6 | SDG alignment is stated | Minor |",
                                                  "| 7.6 | SDG alignment is stated | Major |"), "utf-8")
        self.assertEqual(ds.checklist()["7.6"]["severity"], "major")


# ------------------------------------------------------------------ parser and rules
class TestParser(Sandbox):
    def test_official_form(self):
        s = self.spec("CPE201")
        self.assertEqual((s.course_code, s.course_title), ("CPE201", "Data Structures and Algorithms"))
        self.assertEqual([c.id for c in s.clos], ["CLO1", "CLO2", "CLO3"])
        self.assertEqual([m.level for m in s.methods][:2], ["Understand", "Apply"])
        self.assertEqual(qa_rules.weight_report(s)["sum"], 100)
        self.assertEqual(len(s.grades()), 8)
        self.assertEqual(qa_rules.form_gate(s), [])

    def test_off_form_documents(self):
        for code in ("CPE440", "CPE450"):
            self.assertEqual(len(qa_rules.form_gate(self.spec(code))), 3, code)

    def test_bonus_outside_sum_and_split(self):
        self.assertEqual(qa_rules.weight_report(self.spec("CPE410"))["sum"], 100)
        sp = qa_rules.splits(self.spec("CPE430"))
        self.assertEqual([s["sum"] for s in sp], [28, 28])
        self.assertNotEqual(sp[0]["parts"], sp[1]["parts"])

    def test_clo_levels_match_ground_truth_tables(self):
        """Every 'Derived level' in evaluation/*.md 'CLO analysis' tables."""
        checked = 0
        for f in sorted(EVAL.glob("CPE*.md")):
            text = f.read_text("utf-8")
            if "## CLO analysis" not in text:
                continue
            levels = qa_rules.clo_levels(self.spec(f.stem))
            table = text.split("## CLO analysis", 1)[1].split("##", 1)[0]
            for m in re.finditer(r"^\| (CLO\d+) \| \d+ \| [^|]+ \| ([^|]+) \|", table, re.M):
                exp = m[2].strip()
                exp = None if exp.startswith("none") else exp
                self.assertEqual(levels[m[1]]["level"], exp, f"{f.stem} {m[1]}")
                checked += 1
        self.assertGreater(checked, 30)


class TestRules(unittest.TestCase):
    def test_noun_traps_and_to_clauses(self):
        d = qa_rules.derive_clo
        self.assertEqual(d("Analyze the trade-offs between competing algorithm designs")["level"], "Analyze")
        self.assertEqual(d("Apply cross-validation to select hyperparameters")["level"], "Analyze")
        self.assertEqual(d("Communicate project status and design decisions clearly")["level"], "Apply")
        self.assertIsNone(d("Give students a foundation in game design")["level"])

    def test_verdict_policy_table(self):
        f = lambda sev, st="open": {"id": "F", "severity": sev, "status": st}  # noqa: E731
        self.assertEqual(qa_rules.compute_verdict([f("minor")])["verdict"], "APPROVE")
        self.assertEqual(qa_rules.compute_verdict([f("major"), f("minor")])["verdict"], "REVISE")
        self.assertEqual(qa_rules.compute_verdict([f("blocker"), f("major")])["verdict"], "RETURN")
        self.assertEqual(qa_rules.compute_verdict([f("blocker", "resolved")])["verdict"], "APPROVE")


# ------------------------------------------------------------------- ground truth
class TestGroundTruth(Sandbox):
    def test_deterministic_pipeline_matches_evaluation(self):
        h = self.harness()
        for code, t in gt.load_all(EVAL).items():
            res = pipeline.run_deterministic(h, f"courses/{code}.md")
            s = gt.score(t, ds.load_findings(code), res["verdict"]["verdict"])
            self.assertTrue(s["verdict_ok"], f"{code}: {s['verdict']} != {t.verdict}")
            self.assertEqual(s["misses"], [], code)
            self.assertEqual(s["false_positives"], [], code)
            self.assertEqual(s["severity_accuracy"][0], s["hits"], code)

    def test_plo_rollup_matches_readme(self):
        h = self.harness()
        codes = sorted(gt.load_all(EVAL))
        for c in codes:
            pipeline.run_deterministic(h, f"courses/{c}.md")
        got = {r["plo"]: r["status"] for r in _coverage([f"courses/{c}.md" for c in codes])}
        self.assertEqual(got["PLO6"], "gap")
        self.assertEqual(got["PLO7"], "claimed, not yet approved")
        self.assertEqual(got["PLO1"], "covered")
        self.assertEqual(got["PLO11"], "gap")


# ------------------------------------------------------------ tool + plugin guarantees
class TestToolGuarantees(Sandbox):
    P = "courses/CPE502.md"

    def test_every_tool_is_described_and_permissioned(self):
        for spec in TOOLS.values():
            self.assertTrue(spec.description, spec.name)
            self.assertIn(spec.permission, ("read", "write", "dangerous"))
        self.assertEqual(TOOLS["resolve_finding"].permission, "dangerous")
        self.assertEqual(len(tool_defs(["get_verdict", "get_findings"])), 2)

    def test_owner_from_checklist(self):
        out = self.call("add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                                        "checklist_rule": "4.7", "section": "Assessment table",
                                        "quote": "x", "message": "too high", "suggested_fix": "lower it"}, RW)
        self.assertIn("owned by curriculum-auditor", out["error"])

    def test_severity_and_verdict_are_not_inputs(self):
        sev = self.call("add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                                        "checklist_rule": "4.3", "severity": "minor", "section": "Assessment table",
                                        "quote": "x", "message": "rounding", "suggested_fix": "ignore it"}, RW)
        self.assertIn("severity: Extra inputs", sev["error"])
        self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)
        bad = self.call("write_review_note", {"course_code": "CPE502", "spec_path": self.P, "verdict": "APPROVE"}, RW)
        self.assertFalse(bad["ok"])
        good = self.call("write_review_note", {"course_code": "CPE502", "spec_path": self.P}, RW)
        self.assertEqual(good["result"]["verdict"], "RETURN")
        note = (self.tmp / "reports/CPE502/REVIEW_NOTE.md").read_text("utf-8")
        self.assertEqual(note.count("**Verdict:** "), 1)
        log = json.loads((self.tmp / "reports/audit-log.jsonl").read_text("utf-8").splitlines()[-1])
        self.assertEqual(log["rulebook_sha256"], ds.rulebook_sha256())
        rows = (self.tmp / "reports/amendments-queue.csv").read_text("utf-8").splitlines()
        self.assertIn("Dr. ", rows[1])            # owner = course coordinator from the form

    def test_validator_blocks_direct_edits(self):
        self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)
        f = ds.load_findings("CPE502")
        with self.assertRaisesRegex(ValueError, "severity"):
            ds.save_findings("CPE502", [{**f[0], "severity": "minor"}])
        with self.assertRaisesRegex(ValueError, "removed"):
            ds.save_findings("CPE502", [])

    def test_resolve_needs_dangerous_and_keeps_audit_trail(self):
        self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)
        args = {"course_code": "CPE502", "finding_id": "F001",
                "resolution_note": "Committee accepted the participation note", "resolved_by": "Dr. Chair"}
        self.assertIn("Permission denied", self.call("resolve_finding", args, RW)["error"])
        self.assertTrue(self.call("resolve_finding", args, {"read", "write", "dangerous"})["ok"])
        f = ds.load_findings("CPE502")[0]
        self.assertEqual((f["status"], f["severity"]), ("resolved", "blocker"))

    def test_ground_truth_and_outside_unreadable(self):
        (self.tmp / "evaluation").mkdir()
        (self.tmp / "evaluation" / "CPE502.md").write_text("answers", "utf-8")
        for p in ("evaluation/CPE502.md", "../outside.md", "total-cases/2110511.pdf"):
            self.assertFalse(self.call("read_course_spec", {"path": p})["ok"], p)

    def test_model_judgment_overrides_derivation(self):
        p = "courses/CPE503.md"
        before = self.call("run_bloom_checks", {"path": p})["result"]["findings"]
        self.assertIn("2.2", [f["checklist_rule"] for f in before])
        self.call("set_clo_level", {"course_code": "CPE503", "clo": "CLO1", "level": "Understand",
                                    "verbs": ["give"], "reason": "test override of the derivation"}, RW)
        after = self.call("run_bloom_checks", {"path": p})["result"]["findings"]
        self.assertNotIn("2.2", [f["checklist_rule"] for f in after])

    def test_duplicates_skipped(self):
        a = self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)["result"]
        b = self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)["result"]
        self.assertEqual((a["added"], b["added"], b["skipped_duplicates"]), (1, 0, 1))


# -------------------------------------------------------------------- agent loop (M8)
class TestAgentLoop(Sandbox):
    P = "courses/CPE502.md"

    def test_reviewer_stage_scope_is_enforced(self):
        h = self.harness([
            [("check_form_gate", {"path": self.P})],
            [("resolve_finding", {"course_code": "CPE502", "finding_id": "F001",
                                  "resolution_note": "x" * 12, "resolved_by": "me"})],
            [("record_check_results", {"path": self.P, "check": "bloom"})],
            [("record_check_results", {"path": self.P, "check": "structure"})],
            "CPE502: 1 blocker, weights 95 (-5)",
        ])
        r = run_stage(h, pipeline.STAGES["course-reviewer"], "review", max_steps=8)
        self.assertEqual(r.stopped, "done")
        errs = [c["result"]["error"] for c in r.errors]
        self.assertIn("not available to course-reviewer", errs[0])
        self.assertIn("may only record checks", errs[1])
        self.assertEqual(ds.load_findings("CPE502")[0]["source_agent"], "course-reviewer")
        offered = {t["function"]["name"] for t in h.client.requests[0]["tools"]}
        self.assertNotIn("resolve_finding", offered)

    def test_source_agent_is_injected_not_trusted(self):
        h = self.harness([
            [("add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                              "checklist_rule": "2.7", "section": "Course learning outcomes, row \"CLO4\"",
                              "quote": "| CLO4 |", "message": "Licensing rules fit PLO7 only loosely",
                              "suggested_fix": "Confirm the CLO4 mapping", "standard_ref": "plo-catalog.md"})],
            "done",
        ])
        run_stage(h, pipeline.STAGES["curriculum-auditor"], "audit")
        f = ds.load_findings("CPE502")[0]
        self.assertEqual((f["source_agent"], f["severity"]), ("curriculum-auditor", "minor"))

    def test_writer_cannot_approve_open_blocker(self):
        self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)
        h = self.harness([
            [("write_review_note", {"course_code": "CPE502", "spec_path": self.P, "verdict": "APPROVE"})],
            [("write_review_note", {"course_code": "CPE502", "spec_path": self.P})],
            "CPE502 RETURN",
        ])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=4)
        self.assertFalse(r.calls[0]["result"]["ok"])
        self.assertEqual(r.calls[1]["result"]["result"]["verdict"], "RETURN")

    def test_auditor_skipped_when_form_gate_fails(self):
        h = self.harness([
            [("record_check_results", {"path": "courses/CPE440.md", "check": "structure"})], "F.1 failed",
            [("write_review_note", {"course_code": "CPE440", "spec_path": "courses/CPE440.md"})], "RETURN",
        ])
        res = pipeline.run_agents(h, "courses/CPE440.md")
        self.assertTrue(res["f1_failed"])
        self.assertEqual([s["stage"] for s in res["stages"]], ["course-reviewer", "verdict-writer"])
        self.assertEqual(res["verdict"]["verdict"], "RETURN")

    def test_repeat_call_stops_loop(self):
        same = [("get_findings", {"course_code": "CPE502"})]
        r = run_stage(self.harness([same, same, same]), pipeline.STAGES["verdict-writer"], "write", max_steps=3)
        self.assertEqual(r.stopped, "repeat")

    def test_tool_calls_are_logged(self):
        h = self.harness([[("check_weights", {"path": self.P})], "ok"])
        run_stage(h, pipeline.STAGES["course-reviewer"], "review", run_id="r-test")
        events = [json.loads(x) for x in (self.tmp / "calls.jsonl").read_text("utf-8").splitlines()]
        self.assertEqual([e["event"] for e in events], ["llm_call", "tool_call", "llm_call"])
        self.assertTrue(all(e["run_id"] == "r-test" for e in events))


if __name__ == "__main__":
    unittest.main()
