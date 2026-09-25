"""Test for hooks/log_verdict.py: each audit line names the rulebook version."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "log_verdict.py")
RULES = b"| 4.3 | Weights | Blocker | course-reviewer |\n"


class LogVerdictTest(unittest.TestCase):
    def test_audit_line_names_the_rulebook_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            checklist = os.path.join(tmp, "checklist.md")
            with open(checklist, "wb") as f:
                f.write(RULES)
            course_dir = os.path.join(tmp, "reports", "CPE201")
            os.makedirs(course_dir)
            with open(os.path.join(course_dir, "findings.json"), "w", encoding="utf-8") as f:
                f.write("[]")
            payload = {"tool_name": "Write", "session_id": "test",
                       "tool_input": {"file_path": os.path.join(course_dir, "REVIEW_NOTE.md"),
                                      "content": "**Verdict:** APPROVE"}}
            env = dict(os.environ, COURSE_SPEC_QA_CHECKLIST=checklist)
            proc = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                                  capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(tmp, "reports", "audit-log.jsonl"), encoding="utf-8") as f:
                entry = json.loads(f.read().splitlines()[-1])
            self.assertEqual(entry["rulebook_sha256"], hashlib.sha256(RULES).hexdigest())
            self.assertEqual(entry["verdict"], "APPROVE")


if __name__ == "__main__":
    unittest.main()
