"""Tests for hooks/validate_findings.py, run as a subprocess the way Claude Code runs it."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validate_findings.py")

CHECKLIST = """# Checklist fixture
| ID | Check | Severity | Owner |
|---|---|---|---|
| F.1 | Form gate | Blocker | course-reviewer |
| 2.2 | CLO verb can be classified | Major | curriculum-auditor |
| 4.3 | Weights sum to 100 | Blocker | course-reviewer |
| 4.10 | Split agrees | even with a pipe | Major | course-reviewer |
| 7.1 | Reading list given | Minor | course-reviewer |
"""


def finding(**overrides):
    base = {
        "id": "F001",
        "source_agent": "course-reviewer",
        "checklist_rule": "4.3",
        "severity": "blocker",
        "section": "Assessment table",
        "quote": "| Final project | Bloom's taxonomy (Create) | CLO3 | 40.00 |",
        "standard_ref": None,
        "message": "Weights sum to 95, short by 5.",
        "suggested_fix": "Add the missing 5 points to a component.",
        "status": "open",
    }
    base.update(overrides)
    return base


class ValidateFindingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.checklist = os.path.join(self.tmp.name, "checklist.md")
        with open(self.checklist, "w", encoding="utf-8") as f:
            f.write(CHECKLIST)
        self.target = os.path.join(self.tmp.name, "reports", "CPE502", "findings.json")
        os.makedirs(os.path.dirname(self.target))

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, tool_name, tool_input, checklist=None):
        env = dict(os.environ, COURSE_SPEC_QA_CHECKLIST=checklist or self.checklist)
        payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
        proc = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                              text=True, env=env)
        return proc.returncode, proc.stderr

    def write_current(self, findings):
        with open(self.target, "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=2)

    def write_call(self, findings, path=None):
        return self.run_hook("Write", {"file_path": path or self.target,
                                       "content": json.dumps(findings, indent=2)})

    def test_other_files_are_ignored(self):
        code, _ = self.run_hook("Write", {"file_path": os.path.join(self.tmp.name, "REVIEW_NOTE.md"),
                                          "content": "not json"})
        self.assertEqual(code, 0)

    def test_findings_json_outside_a_reports_course_folder_is_ignored(self):
        path = os.path.join(self.tmp.name, "notes", "findings.json")
        code, _ = self.run_hook("Write", {"file_path": path, "content": "not json"})
        self.assertEqual(code, 0)

    def test_valid_new_file_is_allowed(self):
        self.assertEqual(self.write_call([finding()])[0], 0)

    def test_empty_array_is_allowed(self):
        self.assertEqual(self.write_call([])[0], 0)

    def test_unknown_rule_is_blocked(self):
        code, err = self.write_call([finding(checklist_rule="9.9")])
        self.assertEqual(code, 2)
        self.assertIn("not a rule", err)

    def test_wrong_severity_is_blocked(self):
        code, err = self.write_call([finding(severity="major")])
        self.assertEqual(code, 2)
        self.assertIn("severity", err)

    def test_severity_case_and_spaces_are_ignored(self):
        self.assertEqual(self.write_call([finding(severity=" Blocker ")])[0], 0)

    def test_wrong_owner_is_blocked(self):
        code, err = self.write_call([finding(source_agent="curriculum-auditor")])
        self.assertEqual(code, 2)
        self.assertIn("owned by", err)

    def test_missing_field_is_blocked(self):
        code, err = self.write_call([finding(quote="")])
        self.assertEqual(code, 2)
        self.assertIn("quote", err)

    def test_resolved_needs_a_note(self):
        self.assertEqual(self.write_call([finding(status="resolved")])[0], 2)
        self.assertEqual(self.write_call([finding(status="resolved",
                                                  resolution_note="Human reviewer: weights fixed.")])[0], 0)

    def test_unknown_status_is_blocked(self):
        code, err = self.write_call([finding(status="closed")])
        self.assertEqual(code, 2)
        self.assertIn("Blocked", err)

    def test_duplicate_id_is_blocked(self):
        code, err = self.write_call([finding(), finding()])
        self.assertEqual(code, 2)
        self.assertIn("duplicate", err)

    def test_not_an_array_is_blocked(self):
        code, err = self.run_hook("Write", {"file_path": self.target, "content": json.dumps(finding())})
        self.assertEqual(code, 2)
        self.assertIn("array", err)

    def test_invalid_json_is_blocked(self):
        code, err = self.run_hook("Write", {"file_path": self.target, "content": "[{"})
        self.assertEqual(code, 2)
        self.assertIn("not valid JSON", err)

    def test_removing_an_existing_finding_is_blocked(self):
        self.write_current([finding()])
        code, err = self.write_call([])
        self.assertEqual(code, 2)
        self.assertIn("removed", err)

    def test_changing_an_existing_section_is_blocked(self):
        self.write_current([finding()])
        code, err = self.write_call([finding(section="Grading")])
        self.assertEqual(code, 2)
        self.assertIn("cannot change", err)

    def test_resolving_an_existing_finding_is_allowed(self):
        self.write_current([finding()])
        self.assertEqual(self.write_call([finding(status="resolved",
                                                  resolution_note="Weights corrected.")])[0], 0)

    def test_appending_is_allowed(self):
        self.write_current([finding()])
        second = finding(id="F002", source_agent="curriculum-auditor", checklist_rule="2.2",
                         severity="major", section="CLO table, row CLO1")
        self.assertEqual(self.write_call([finding(), second])[0], 0)

    def test_edit_is_validated_against_the_result(self):
        self.write_current([finding()])
        code, err = self.run_hook("Edit", {"file_path": self.target,
                                           "old_string": '"severity": "blocker"',
                                           "new_string": '"severity": "minor"'})
        self.assertEqual(code, 2)
        self.assertIn("Blocked", err)

    def test_edit_replace_all_is_applied_to_every_match(self):
        one = finding(id="F001", checklist_rule="7.1", severity="minor", section="Reading list")
        two = finding(id="F002", checklist_rule="7.1", severity="minor", section="Reading list")
        self.write_current([one, two])
        code, err = self.run_hook("Edit", {"file_path": self.target, "old_string": '"status": "open"',
                                           "new_string": '"status": "resolved"', "replace_all": True})
        self.assertEqual(code, 2)  # both resolved, neither has a resolution_note
        self.assertIn("Blocked", err)

    def test_resulting_content_matches_edit_semantics(self):
        spec = importlib.util.spec_from_file_location("validate_findings", HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        first_only = module.resulting_content("Edit", {"old_string": "a", "new_string": "b"}, "a a")
        every = module.resulting_content("Edit", {"old_string": "a", "new_string": "b",
                                                  "replace_all": True}, "a a")
        self.assertEqual(first_only, "b a")
        self.assertEqual(every, "b b")

    def test_edit_whose_old_string_is_absent_is_left_to_the_tool(self):
        self.write_current([finding()])
        code, _ = self.run_hook("Edit", {"file_path": self.target, "old_string": "no such text",
                                         "new_string": "x"})
        self.assertEqual(code, 0)

    def test_missing_checklist_blocks(self):
        code, err = self.run_hook("Write", {"file_path": self.target, "content": "[]"},
                                  checklist=os.path.join(self.tmp.name, "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("checklist.md", err)

    def test_pipe_inside_check_text_keeps_severity_and_owner(self):
        self.assertEqual(self.write_call([finding(checklist_rule="4.10", severity="major")])[0], 0)
        self.assertEqual(self.write_call([finding(checklist_rule="4.10", severity="blocker")])[0], 2)

    def test_backslash_path_is_recognised(self):
        path = "C:\\course\\reports\\CPE502\\findings.json"
        code, err = self.run_hook("Write", {"file_path": path, "content": "[{"})
        self.assertEqual(code, 2)
        self.assertIn("Blocked", err)

    def test_bom_is_accepted(self):
        code, _ = self.run_hook("Write", {"file_path": self.target,
                                          "content": "\ufeff" + json.dumps([finding()])})
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
