"""Tests for the boomi-conventions hooks (run: python3 -m unittest discover -s plugins/boomi-conventions/tests)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")


def process_xml(name, start="<passthroughaction/>", prop="PP_BATCH_ID"):
    return (f'<?xml version="1.0" encoding="UTF-8"?><bns:Component xmlns:bns="http://api.platform.boomi.com/" '
            f'componentId="" name="{name}" type="process" version="1"><bns:object><process><shapes>'
            f'<shape shapetype="start"><configuration>{start}</configuration></shape>'
            f'<shape shapetype="documentproperties"><documentproperty propertyId="process.{prop}"/></shape>'
            f'</shapes></process></bns:object></bns:Component>')


def run(script, payload):
    out = subprocess.run([sys.executable, os.path.join(HOOKS, script)], input=json.dumps(payload),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out.strip() else None


class CheckNamesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = self.dir.name
        os.mkdir(os.path.join(self.cwd, "active-development"))

    def tearDown(self):
        self.dir.cleanup()

    def path(self, name="p.xml"):
        return os.path.join(self.cwd, name)

    def write_call(self, content, name="p.xml"):
        return run("check_boomi_names.py", {"cwd": self.cwd, "tool_name": "Write",
                                            "tool_input": {"file_path": self.path(name), "content": content}})

    def reason(self, result):
        self.assertIsNotNone(result)
        out = result["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        return out["permissionDecisionReason"]

    def test_conforming_subprocess_passes(self):
        self.assertIsNone(self.write_call(process_xml("[S] Load orders")))

    def test_new_dpp_is_denied_with_fix(self):
        reason = self.reason(self.write_call(process_xml("[S] Load orders", prop="DPP_BATCH_ID")))
        self.assertIn("use PP_BATCH_ID", reason)

    def test_new_ddp_is_denied_with_fix(self):
        xml = process_xml("[S] X").replace("process.PP_BATCH_ID", "dynamicdocument.DDP_SEGMENT")
        self.assertIn("use D_SEGMENT", self.reason(self.write_call(xml)))

    def test_subprocess_without_prefix_is_denied(self):
        self.assertIn('"[S] Load orders"', self.reason(self.write_call(process_xml("Load orders"))))

    def test_ut_process_and_main_process_pass(self):
        self.assertIsNone(self.write_call(process_xml("[UT] Load orders - ok")))
        self.assertIsNone(self.write_call(process_xml("Orders listener", start="<noaction/>")))

    def test_existing_names_in_pulled_component_are_kept(self):
        old = process_xml("Legacy sub", prop="DPP_OLD")
        with open(self.path(), "w", encoding="utf-8") as f:
            f.write(old)
        # rewriting the pulled file with a change elsewhere: DPP_OLD and the old name are not new
        self.assertIsNone(self.write_call(old.replace('version="1"', 'version="2"')))
        edit = run("check_boomi_names.py", {"cwd": self.cwd, "tool_name": "Edit", "tool_input": {
            "file_path": self.path(), "old_string": "process.DPP_OLD", "new_string": "process.DPP_NEW"}})
        self.assertIn("use PP_NEW", self.reason(edit))

    def test_allow_file(self):
        with open(os.path.join(self.cwd, ".boomi-naming-allow"), "w", encoding="utf-8") as f:
            f.write("# agreed with team X\nDPP_SHARED\n")
        self.assertIsNone(self.write_call(process_xml("[S] X", prop="DPP_SHARED")))

    def test_name_used_elsewhere_in_workspace_is_kept(self):
        # a pulled parent sets DPP_ORDER_ID: a new [S] or [UT] that reads it must keep the name
        os.mkdir(os.path.join(self.cwd, "active-development", "process"))
        with open(os.path.join(self.cwd, "active-development", "process", "parent.xml"), "w", encoding="utf-8") as f:
            f.write(process_xml("Orders listener", start="<noaction/>", prop="DPP_ORDER_ID"))
        self.assertIsNone(self.write_call(process_xml("[S] Load orders", prop="DPP_ORDER_ID")))
        self.assertIn("use PP_OTHER", self.reason(self.write_call(process_xml("[S] Load orders", prop="DPP_OTHER"))))

    def test_outside_boomi_workspace_ignored(self):
        os.rmdir(os.path.join(self.cwd, "active-development"))
        self.assertIsNone(self.write_call(process_xml("Load orders", prop="DPP_X")))

    def test_xml_that_is_not_a_component_ignored(self):
        self.assertIsNone(self.write_call('<?xml version="1.0"?><config><key>DPP_X</key></config>', name="pom.xml"))

    def test_non_xml_and_other_commands_ignored(self):
        self.assertIsNone(self.write_call("DPP_X", name="notes.md"))
        self.assertIsNone(run("check_boomi_names.py", {"cwd": self.cwd, "tool_name": "Bash",
                                                       "tool_input": {"command": "ls DPP_X.xml"}}))

    def test_create_script_checks_whole_file(self):
        with open(self.path(), "w", encoding="utf-8") as f:
            f.write(process_xml("Sub", prop="DPP_X"))
        result = run("check_boomi_names.py", {"cwd": self.cwd, "tool_name": "Bash", "tool_input": {
            "command": "bash scripts/boomi-component-create.sh p.xml"}})
        reason = self.reason(result)
        self.assertIn("use PP_X", reason)
        self.assertIn('"[S] Sub"', reason)


class SessionContextTest(unittest.TestCase):
    def test_only_in_boomi_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(run("session_context.py", {"cwd": d}))
            os.mkdir(os.path.join(d, "active-development"))
            ctx = run("session_context.py", {"cwd": d})["hookSpecificOutput"]["additionalContext"]
            self.assertIn("take precedence", ctx)

    def test_env_with_boomi_variables(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".env"), "w", encoding="utf-8") as f:
                f.write("BOOMI_ACCOUNT_ID=x\n")
            self.assertIsNotNone(run("session_context.py", {"cwd": d}))


if __name__ == "__main__":
    unittest.main()
