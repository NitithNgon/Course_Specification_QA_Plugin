"""Offline tests for Session 3 (W11): agent loop (M8), state machine (M9), classifier (M10),
router (M11). No Ollama: FakeClient replays scripted model outputs.

    python -m unittest discover -s tests -v          (from Course_Specification_QA_Plugin_harness/)

Transitions are unit-tested without calling the LLM, as the slides ask.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import LLMConnectionError, load_config  # noqa: E402
from harness import data_store as ds, pipeline, state_machine as sm  # noqa: E402
from harness.agent_loop import run_stage  # noqa: E402
from harness.classifier import by_rules, classify, facts_of  # noqa: E402
from harness.router import route  # noqa: E402
from test_offline import Sandbox  # noqa: E402

S = sm.S
P = "courses/CPE502.md"            # standard: on the form, every CLO verb classified; gold RETURN
P501 = "courses/CPE501.md"         # standard, with Bloom findings for the auditor to record; gold REVISE


class Crash(BaseException):
    """Not an Exception: stands in for the process dying mid-run."""


def reviewer(path=P):
    return [[("check_form_gate", {"path": path})],
            [("record_check_results", {"path": path, "check": "structure"})], "reviewed"]


def auditor(path=P):
    return [[("derive_clo_levels", {"path": path})],
            [("record_check_results", {"path": path, "check": "bloom"})],
            [("record_check_results", {"path": path, "check": "plo"})], "audited"]


def writer(code="CPE502", path=P):
    return [[("write_review_note", {"course_code": code, "spec_path": path})], "written"]


class W11(Sandbox):
    def events(self, name=None):
        ev = [json.loads(x) for x in (self.tmp / "calls.jsonl").read_text("utf-8").splitlines()]
        return [e for e in ev if name is None or e["event"] == name]

    def models(self, h):
        return [r["model"] for r in h.client.requests]

    def model_of(self, h, profile):
        return h.config.profile(profile).model


# ------------------------------------------------------------------------ M8 agent loop
class TestAgentLoop(W11):
    def test_completion_check_catches_early_stop_and_restates_goal(self):
        h = self.harness(["done already", [("record_check_results", {"path": P, "check": "structure"})], "done"])
        r = run_stage(h, pipeline.STAGES["course-reviewer"], "review CPE502",
                      check=lambda: pipeline.CHECKS["course-reviewer"](P))
        self.assertEqual((r.stopped, r.steps), ("done", 3))
        nudge = h.client.requests[1]["messages"][-1]
        self.assertEqual(nudge["role"], "user")
        self.assertIn("Not finished: findings.json does not exist", nudge["content"])
        self.assertIn("Goal: review CPE502", nudge["content"])
        self.assertEqual([e["ok"] for e in self.events("completion_check")], [False, True])

    def test_error_budget_stops_and_logs_safe_failure(self):
        bad = [("made_up_tool", {})]
        h = self.harness([bad, [("other_made_up", {})], "never reached"])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_errors=2)
        self.assertEqual((r.stopped, r.steps), ("error_budget", 2))
        self.assertEqual(self.events("safe_failure")[-1]["reason"], "error_budget")

    def test_limit_after_the_work_is_done_counts_as_verified(self):
        self.call("record_check_results", {"path": P, "check": "structure"}, {"read", "write"})
        h = self.harness([[("write_review_note", {"course_code": "CPE502", "spec_path": P})],
                          [("get_findings", {"course_code": "CPE502"})]])     # loops instead of answering
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=2,
                      check=lambda: pipeline.CHECKS["verdict-writer"](P))
        self.assertEqual((r.stopped, r.verified, r.ok), ("max_steps", True, True))
        self.assertEqual(self.events("safe_failure"), [])
        self.assertEqual(self.events("completion_check")[-1]["after"], "max_steps")

    def test_max_steps_is_a_logged_safe_failure_with_a_trace(self):
        h = self.harness([[("get_findings", {"course_code": "CPE502"})], [("get_verdict", {"course_code": "CPE502"})]])
        r = run_stage(h, pipeline.STAGES["verdict-writer"], "write", max_steps=2, profile="fast")
        self.assertEqual(r.stopped, "max_steps")
        self.assertEqual([t["step"] for t in r.trace], [1, 2])
        self.assertEqual(r.profile, "fast")
        self.assertEqual(self.events("safe_failure")[-1]["reason"], "max_steps")
        self.assertEqual([e["step"] for e in self.events("llm_call")], [1, 2])


# ------------------------------------------------------------------- M9 transitions
class TestTransitions(unittest.TestCase):
    def test_table_is_the_slide_table(self):
        self.assertEqual(sm.TRANSITIONS[S.INTAKE], {S.CLASSIFY})
        self.assertEqual(sm.TRANSITIONS[S.VERIFY], {S.DONE, S.PLAN, S.ESCALATE})
        for s in (S.CLASSIFY, S.PLAN, S.ACT, S.VERIFY):
            self.assertIn(S.ESCALATE, sm.TRANSITIONS[s])
        self.assertNotIn(S.ESCALATE, sm.TRANSITIONS[S.INTAKE])
        self.assertTrue(sm.TERMINAL.isdisjoint(sm.TRANSITIONS))

    def test_advance_records_history_and_rejects_illegal_moves(self):
        run = sm.RunState(run_id="r-t", path=P)
        for nxt in (S.CLASSIFY, S.PLAN, S.ACT, S.VERIFY, S.PLAN, S.ACT, S.VERIFY, S.DONE):
            sm.advance(run, nxt, "ok")
        self.assertEqual(len(run.history), 8)
        with self.assertRaises(sm.IllegalTransition):
            sm.advance(run, S.PLAN)                       # DONE is terminal
        with self.assertRaises(sm.IllegalTransition):
            sm.advance(sm.RunState(run_id="r-u", path=P), S.ACT)   # INTAKE -> ACT skips states

    def test_every_task_type_has_a_plan_ending_with_the_writer(self):
        for task_type in ("off_form", "standard", "needs_judgment"):
            plan = sm.PLANS[task_type]
            self.assertEqual((plan[0][0], plan[-1][0]), ("course-reviewer", "verdict-writer"))
        self.assertNotIn("curriculum-auditor", [s for s, _ in sm.PLANS["off_form"]])


# ----------------------------------------------------------------- M10 classifier
class TestClassifier(W11):
    def test_rules_decide_every_course(self):
        got = {Path(p).stem: by_rules(facts_of(p)).task_type for p in ds.list_specs()}
        self.assertEqual(got.pop("CPE440"), "off_form")
        self.assertEqual(got.pop("CPE450"), "off_form")
        self.assertEqual(got.pop("CPE503"), "needs_judgment")     # CLO1 "Give students ..."
        self.assertEqual(set(got.values()), {"standard"})

    def test_small_model_then_main_llm_with_validation(self):
        facts = {**facts_of(P), "clos": 0}                         # on the form, no CLO rows: rules undecided
        self.assertIsNone(by_rules(facts))
        h = self.harness(["not json",
                          '{"task_type": "off_form", "reason": "looks odd"}',      # contradicts the gate
                          '{"task_type": "standard", "reason": "on the form"}'])
        c, how = classify(h, facts, run_id="r-c")
        self.assertEqual((c.task_type, how), ("standard", "main LLM"))
        self.assertEqual(self.models(h), [self.model_of(h, "fast")] * 2 + [self.model_of(h, "reasoning")])
        self.assertEqual([e["valid"] for e in self.events("llm_call")], [False, False, True])
        self.assertIn("contradicts the form gate", self.events("llm_call")[1]["error"])

    def test_undecided_returns_none(self):
        h = self.harness(["x", "y", "z", "w"])
        c, how = classify(h, {**facts_of(P), "methods": 0})
        self.assertEqual((c, how), (None, "undecided"))


# --------------------------------------------------------------------- M11 router
class TestRouter(W11):
    def test_table_long_context_and_fallback(self):
        h = self.harness()
        self.assertEqual(route(h, "audit"), "fast")
        self.assertEqual(route(h, "review"), "reasoning")
        self.assertEqual(route(h, "no-such-kind"), "reasoning")             # default
        self.assertEqual(route(h, "audit", ctx_tokens=7000), "reasoning")   # > 0.8 x 8192
        self.assertEqual(route(h, "write", failures=1), "reasoning")        # one rung up
        self.assertEqual(route(h, "write", failures=9), "reasoning")        # capped at the top
        rules = [e["rule"] for e in self.events("route")]
        self.assertEqual(rules, ["table", "table", "default", "long_context", "table+fallback", "table+fallback"])

    def test_unknown_profile_in_routing_fails_at_load(self):
        cfg = (ROOT / "config.yaml").read_text("utf-8").replace("judge:    reasoning", "judge:    huge")
        (self.tmp / "bad.yaml").write_text(cfg, "utf-8")
        with self.assertRaisesRegex(KeyError, "huge"):
            load_config(self.tmp / "bad.yaml")


# ------------------------------------------------------------- M9 end to end (FakeClient)
class TestStateMachine(W11):
    def test_standard_course_reaches_done_with_routed_profiles(self):
        h = self.harness(reviewer() + auditor() + writer())
        res = sm.run_sm(h, P)
        self.assertEqual((res["state"], res["task_type"], res["classified_by"]), ("done", "standard", "rules"))
        self.assertEqual(res["verdict"]["verdict"], "RETURN")
        self.assertEqual([t.split(":")[0] for t in res["transitions"]],
                         ["INTAKE -> CLASSIFY", "CLASSIFY -> PLAN", "PLAN -> ACT", "ACT -> VERIFY", "VERIFY -> DONE"])
        fast, reasoning = self.model_of(h, "fast"), self.model_of(h, "reasoning")
        self.assertEqual(self.models(h), [reasoning] * 3 + [fast] * 4 + [fast] * 2)
        offered = {t["function"]["name"] for t in h.client.requests[3]["tools"]}
        self.assertNotIn("set_clo_level", offered)                          # "audit" allow-list
        saved = sm.store_for(h).load(res["run_id"])
        self.assertEqual((saved.state, len(saved.history)), (S.DONE, 5))
        self.assertEqual([e["dst"] for e in self.events("transition")], ["classify", "plan", "act", "verify", "done"])

    def test_off_form_skips_auditor_with_narrow_tools(self):
        p = "courses/CPE440.md"
        h = self.harness(reviewer(p) + writer("CPE440", p))
        res = sm.run_sm(h, p)
        self.assertEqual((res["task_type"], res["verdict"]["verdict"]), ("off_form", "RETURN"))
        self.assertEqual([s["stage"] for s in res["stages"]], ["course-reviewer", "verdict-writer"])
        self.assertEqual([t["function"]["name"] for t in h.client.requests[0]["tools"]], sm.NARROW["gate"])

    def test_needs_judgment_routes_auditor_to_reasoning(self):
        p = "courses/CPE503.md"
        h = self.harness([[("record_check_results", {"path": p, "check": "structure"})], "reviewed",
                          [("set_clo_level", {"course_code": "CPE503", "clo": "CLO1", "level": None,
                                              "reason": "describes what the course gives, a teaching aim"})],
                          *auditor(p)[1:], *writer("CPE503", p)])
        res = sm.run_sm(h, p)
        self.assertEqual((res["state"], res["task_type"]), ("done", "needs_judgment"))
        self.assertEqual([(s["kind"], s["profile"]) for s in res["stages"]],
                         [("review", "reasoning"), ("judge", "reasoning"), ("write", "fast")])

    def test_early_stop_replans_with_a_stronger_profile(self):
        h = self.harness(reviewer(P501) + ["audited"] * 3 + auditor(P501)[1:] + writer("CPE501", P501))
        h.config.agents["curriculum-auditor"] = {"max_steps": 3}
        res = sm.run_sm(h, P501)
        self.assertEqual((res["state"], res["replans"], res["verdict"]["verdict"]), ("done", 1, "REVISE"))
        self.assertIn("VERIFY -> PLAN", [t.split(":")[0] for t in res["transitions"]])
        audits = [s for s in res["stages"] if s["stage"] == "curriculum-auditor"]
        self.assertEqual([(a["stopped"], a["verified"], a["profile"], a["attempt"]) for a in audits],
                         [("max_steps", False, "fast", 1), ("done", True, "reasoning", 2)])
        retry_task = h.client.requests[6]["messages"][1]["content"]
        self.assertIn("An earlier attempt did not finish", retry_task)

    def test_escalates_after_two_replans_without_a_verdict(self):
        h = self.harness(reviewer(P501) + ["audited"] * 3)
        h.config.agents["curriculum-auditor"] = {"max_steps": 1}
        res = sm.run_sm(h, P501)
        self.assertEqual((res["state"], res["replans"], res["verdict"]["verdict"]), ("escalate", 2, "ESCALATED"))
        d = self.tmp / "reports" / "CPE501"
        self.assertTrue((d / "ESCALATION.md").is_file())
        self.assertFalse((d / "REVIEW_NOTE.md").exists())                   # nothing unverified published
        self.assertEqual([s["profile"] for s in res["stages"]][1:], ["fast", "reasoning", "reasoning"])
        self.assertEqual(len(self.events("escalate")), 1)
        pipeline.finish_batch(h, [P501], ["CPE501"])
        self.assertIn("| ESCALATED |", (self.tmp / "reports" / "COURSE_SPEC_REVIEW.md").read_text("utf-8"))

    def test_runtime_error_escalates(self):
        h = self.harness([LLMConnectionError("Cannot reach http://localhost:11434")])
        res = sm.run_sm(h, P)
        self.assertEqual(res["state"], "escalate")
        self.assertIn("LLMConnectionError", res["transitions"][-1])

    def test_resume_after_crash_continues_from_checkpoint(self):
        h = self.harness(reviewer() + [Crash()])
        with self.assertRaises(Crash):
            sm.run_sm(h, P)
        run_id, _, state, _ = sm.store_for(h).runs()[0]
        saved = sm.store_for(h).load(run_id)
        self.assertEqual((state, [s.done for s in saved.plan]), ("act", [True, False, False]))

        h2 = self.harness(auditor() + writer())
        res = sm.resume(h2, run_id)
        self.assertEqual((res["state"], res["verdict"]["verdict"]), ("done", "RETURN"))
        self.assertIn("curriculum-auditor", h2.client.requests[0]["messages"][0]["content"])
        self.assertEqual(len(res["transitions"]), 5)


if __name__ == "__main__":
    unittest.main()
