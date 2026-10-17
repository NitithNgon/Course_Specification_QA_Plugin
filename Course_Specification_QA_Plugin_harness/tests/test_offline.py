"""Offline tests: no Ollama needed. A FakeClient replays scripted tool calls.

    python -m unittest discover -s tests -v

Every test runs against a scratch copy of courses/ and references/, never the real reports/.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import ChatResult, Harness, execute, tool_defs, TOOLS  # noqa: E402
from harness import data_store as ds, pipeline, qa_rules  # noqa: E402
from harness.agent_loop import run_stage  # noqa: E402
from harness.spec_parser import parse_spec  # noqa: E402

PLUGIN = ds.HARNESS_ROOT.parent
RW = {"read", "write"}


class FakeClient:
    """Returns queued outputs in order. A list item is a list of (tool, args) calls; a str is the final text."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def chat(self, model, messages, **kw):
        self.requests.append({"model": model, "messages": list(messages), **kw})
        out = self.outputs.pop(0)
        if isinstance(out, list):
            calls = [{"function": {"name": n, "arguments": a}} for n, a in out]
            return ChatResult(model=model, content="", tool_calls=calls,
                              message={"role": "assistant", "content": "", "tool_calls": calls},
                              wall_s=0.01)
        return ChatResult(model=model, content=out, message={"role": "assistant", "content": out},
                          wall_s=0.01)


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qa_test_"))
        for d in ("courses", "references"):
            shutil.copytree(PLUGIN / d, self.tmp / d)
        ds.configure(self.tmp)

    def tearDown(self):
        ds.configure(PLUGIN, reports=ds.HARNESS_ROOT / "reports")
        shutil.rmtree(self.tmp, ignore_errors=True)

    def harness(self, outputs=()):
        return Harness(client=FakeClient(outputs), log_file=self.tmp / "calls.jsonl")

    def call(self, name, args, allowed=frozenset({"read"})):
        return execute({"function": {"name": name, "arguments": args}}, allowed=set(allowed))


# ----------------------------------------------------------------- parser + rules
class TestParser(Sandbox):
    def test_clean_spec(self):
        s = parse_spec((self.tmp / "courses/clean_01_data_structures.md").read_text("utf-8"))
        self.assertEqual((s.course_code, s.course_name), ("CPE201", "Data Structures and Algorithms"))
        self.assertEqual([c.id for c in s.clos], ["CLO1", "CLO2", "CLO3"])
        self.assertEqual(s.clos[1].plos, ["PLO3"])
        self.assertEqual(sum(a.weight for a in s.assessments), 100)
        self.assertEqual(s.assessments[0].clos, ["CLO1", "CLO2"])
        self.assertEqual(len(s.policies), 5)
        self.assertGreater(s.rubric_items, 0)

    def test_dash_means_no_plo(self):
        s = parse_spec((self.tmp / "courses/blocker_03_missing_plo.md").read_text("utf-8"))
        self.assertEqual(s.clos[0].plos, [])


class TestRules(unittest.TestCase):
    def test_verb_chain_takes_highest(self):
        self.assertEqual(qa_rules.classify_clo("Design, develop and evaluate a compiler")["level"],
                         "Create")
        self.assertEqual(qa_rules.classify_clo("Define the term entropy")["level"], "Remember")
        self.assertIsNone(qa_rules.classify_clo("Give students a foundation")["level"])

    def test_verdict_policy_table(self):
        f = lambda sev, st="open": {"id": "F", "severity": sev, "status": st}  # noqa: E731
        self.assertEqual(qa_rules.compute_verdict([f("minor")])["verdict"], "APPROVE")
        self.assertEqual(qa_rules.compute_verdict([f("major"), f("minor")])["verdict"], "REVISE")
        self.assertEqual(qa_rules.compute_verdict([f("blocker"), f("major")])["verdict"], "RETURN")
        self.assertEqual(qa_rules.compute_verdict([f("blocker", "resolved")])["verdict"], "APPROVE")


class TestGold(Sandbox):
    def test_deterministic_pipeline_matches_gold(self):
        gold = json.loads((self.tmp / "courses/gold-labels.json").read_text("utf-8"))["cases"]
        h = self.harness()
        for g in gold:
            res = pipeline.run_deterministic(h, f"courses/{g['file']}")
            self.assertEqual(res["verdict"]["verdict"], g["expected_verdict"], g["file"])
            if g["category"] == "clean":
                self.assertEqual(res["verdict"]["open_counts"]["blocker"], 0, g["file"])

    def test_bloom_mismatch_is_located(self):
        out = self.call("run_bloom_check", {"path": "courses/blocker_01_bloom_mismatch.md"})
        rules = {(f["checklist_rule"], f["section"].split("-> ")[-1]) for f in out["result"]["findings"]}
        self.assertIn(("2.4", "CLO2"), rules)


# ------------------------------------------------------------ tool + executor guarantees
class TestToolGuarantees(Sandbox):
    def test_every_tool_is_described_and_permissioned(self):
        for spec in TOOLS.values():
            self.assertTrue(spec.description, spec.name)
            self.assertIn(spec.permission, ("read", "write", "dangerous"))
        self.assertEqual(TOOLS["resolve_finding"].permission, "dangerous")
        self.assertEqual(len(tool_defs(["get_verdict", "get_findings"])), 2)

    def test_cannot_downgrade_checklist_severity(self):
        out = self.call("add_finding", {"course_code": "CPE502", "source_agent": "course-reviewer",
                                        "checklist_rule": "3.3", "severity": "minor",
                                        "section": "Section 3", "quote": "Total: 95",
                                        "message": "rounding", "suggested_fix": "none needed"}, RW)
        self.assertFalse(out["ok"])
        self.assertIn("fixed at 'blocker'", out["error"])

    def test_auditor_must_cite(self):
        out = self.call("add_finding", {"course_code": "CPE501", "source_agent": "curriculum-auditor",
                                        "checklist_rule": "2.4", "severity": "major",
                                        "section": "Section 2 -> CLO2", "quote": "Define",
                                        "message": "verb mismatch", "suggested_fix": "reword it"}, RW)
        self.assertIn("standard_ref", out["error"])

    def test_verdict_is_not_an_input(self):
        p = "courses/blocker_02_weight_95.md"
        self.call("record_check_results", {"path": p, "check": "structure"}, RW)
        bad = self.call("write_review_note", {"course_code": "CPE502", "spec_path": p,
                                              "verdict": "APPROVE"}, RW)
        self.assertFalse(bad["ok"])
        good = self.call("write_review_note", {"course_code": "CPE502", "spec_path": p}, RW)
        self.assertEqual(good["result"]["verdict"], "RETURN")
        note = (self.tmp / "reports/CPE502/REVIEW_NOTE.md").read_text("utf-8")
        self.assertEqual(note.count("**Verdict:** "), 1)
        self.assertIn("**Verdict:** RETURN", note)
        log = (self.tmp / "reports/audit-log.jsonl").read_text("utf-8").splitlines()
        self.assertEqual(json.loads(log[-1])["verdict"], "RETURN")
        self.assertTrue((self.tmp / "reports/amendments-queue.csv").is_file())

    def test_resolve_needs_dangerous_and_keeps_audit_trail(self):
        p = "courses/blocker_02_weight_95.md"
        self.call("record_check_results", {"path": p, "check": "structure"}, RW)
        args = {"course_code": "CPE502", "finding_id": "F001",
                "resolution_note": "Committee accepted 95 + 5 attendance", "resolved_by": "Dr. Chair"}
        self.assertIn("Permission denied", self.call("resolve_finding", args, RW)["error"])
        self.assertTrue(self.call("resolve_finding", args, {"read", "write", "dangerous"})["ok"])
        f = ds.load_findings("CPE502")[0]
        self.assertEqual((f["status"], f["severity"]), ("resolved", "blocker"))  # not deleted

    def test_gold_and_outside_files_unreadable(self):
        for p in ("courses/gold-labels.json", "../outside.md"):
            self.assertFalse(self.call("read_course_spec", {"path": p})["ok"], p)

    def test_duplicate_findings_skipped(self):
        p = "courses/blocker_03_missing_plo.md"
        a = self.call("record_check_results", {"path": p, "check": "structure"}, RW)["result"]
        b = self.call("record_check_results", {"path": p, "check": "plo"}, RW)["result"]
        self.assertGreater(a["added"], 0)
        self.assertGreaterEqual(b["skipped_duplicates"], 1)  # 2.5 on CLO1 found by both stages


# -------------------------------------------------------------------- agent loop (M8)
class TestAgentLoop(Sandbox):
    P = "courses/blocker_02_weight_95.md"

    def test_reviewer_stage_scope_is_enforced(self):
        h = self.harness([
            [("parse_course_spec", {"path": self.P})],
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
                              "checklist_rule": "plo-fit", "severity": "minor",
                              "section": "Section 2 -> CLO3", "quote": "PLO3",
                              "message": "Game level design fits PLO3 only loosely",
                              "suggested_fix": "Consider PLO9 for the team aspect",
                              "standard_ref": "plo-catalog.md"})],
            "done",
        ])
        run_stage(h, pipeline.STAGES["curriculum-auditor"], "audit")
        self.assertEqual(ds.load_findings("CPE502")[0]["source_agent"], "curriculum-auditor")

    def test_writer_cannot_approve_open_blocker(self):
        self.call("record_check_results", {"path": self.P, "check": "structure"}, RW)
        h = self.harness([
            [("write_review_note", {"course_code": "CPE502", "spec_path": self.P,
                                    "verdict": "APPROVE"})],
            [("write_review_note", {"course_code": "CPE502", "spec_path": self.P})],
            "CPE502 RETURN",
        ])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=4)
        self.assertFalse(r.calls[0]["result"]["ok"])
        self.assertEqual(r.calls[1]["result"]["result"]["verdict"], "RETURN")

    def test_repeat_call_stops_loop(self):
        same = [("get_findings", {"course_code": "CPE502"})]
        h = self.harness([same, same, same])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=3)
        self.assertEqual(r.stopped, "repeat")

    def test_max_steps(self):
        h = self.harness([[("get_findings", {"course_code": "CPE50" + str(i)})] for i in range(3)])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=3)
        self.assertEqual((r.stopped, r.steps), ("max_steps", 3))

    def test_tool_calls_are_logged(self):
        h = self.harness([[("check_weights", {"path": self.P})], "ok"])
        run_stage(h, pipeline.STAGES["course-reviewer"], "review", run_id="r-test")
        events = [json.loads(x) for x in (self.tmp / "calls.jsonl").read_text("utf-8").splitlines()]
        self.assertEqual([e["event"] for e in events], ["llm_call", "tool_call", "llm_call"])
        self.assertTrue(all(e["run_id"] == "r-test" for e in events))


if __name__ == "__main__":
    unittest.main()
