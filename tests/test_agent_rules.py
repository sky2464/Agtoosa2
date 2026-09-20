"""Automated test suite for Universal AI Agent Workflow Enforcement (DEV-058)."""

import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.cli.main import main
from agtoosa.core.agent_rules import (
    AgentWorkflowEnforcer,
    RULES_START_TAG,
    RULES_END_TAG,
)


class TestAgentWorkflowEnforcer(unittest.TestCase):
    """Verify non-destructive agent instruction injection across multi-agent targets."""

    def test_fresh_installation_all_targets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            enforcer = AgentWorkflowEnforcer(root)
            self.assertFalse(enforcer.is_enforced())

            res = enforcer.install_all(with_git_hooks=False)
            self.assertTrue(res["is_enforced"])
            self.assertTrue(enforcer.is_enforced())

            # Check created files
            agents_md = root / "AGENTS.md"
            claude_md = root / "CLAUDE.md"
            cursor_mdc = root / ".cursor" / "rules" / "agtoosa.mdc"
            windsurf_rules = root / ".windsurfrules"
            copilot_md = root / ".github" / "copilot-instructions.md"

            for f in [agents_md, claude_md, cursor_mdc, windsurf_rules, copilot_md]:
                self.assertTrue(f.exists(), f"File {f} must exist")
                content = f.read_text(encoding="utf-8")
                self.assertIn(RULES_START_TAG, content)
                self.assertIn(RULES_END_TAG, content)
                self.assertIn("agtoosa query", content)
                self.assertIn("agtoosa graph build", content)
                self.assertIn("agtoosa review", content)

    def test_non_destructive_preservation_of_existing_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            agents_md = root / "AGENTS.md"
            original_user_content = "# My Custom Project Rules\n\n- Always use pytest\n- Never commit secrets\n"
            agents_md.write_text(original_user_content, encoding="utf-8")

            enforcer = AgentWorkflowEnforcer(root)
            enforcer.install_all(targets=["agents"], with_git_hooks=False)

            updated = agents_md.read_text(encoding="utf-8")
            self.assertIn("# My Custom Project Rules", updated)
            self.assertIn("- Always use pytest", updated)
            self.assertIn(RULES_START_TAG, updated)
            self.assertIn(RULES_END_TAG, updated)

            # Second run must replace cleanly without duplicating
            enforcer.install_all(targets=["agents"], with_git_hooks=False)
            twice_updated = agents_md.read_text(encoding="utf-8")
            self.assertEqual(twice_updated.count(RULES_START_TAG), 1)
            self.assertEqual(twice_updated.count(RULES_END_TAG), 1)
            self.assertIn("- Always use pytest", twice_updated)

    def test_cli_agent_init_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            import io
            from contextlib import redirect_stdout

            # Run agtoosa agent-init inside temp directory
            import os
            orig_cwd = os.getcwd()
            try:
                os.chdir(root)
                f = io.StringIO()
                with redirect_stdout(f):
                    ret = main(["agent-init", "--no-git-hooks", "--json"])
                self.assertEqual(ret, 0)
                data = json.loads(f.getvalue())
                self.assertTrue(data["is_enforced"])
                self.assertIn("AGENTS.md", data["installed_files"])
                self.assertIn("CLAUDE.md", data["installed_files"])

                # Test autopilot and setup aliases
                f2 = io.StringIO()
                with redirect_stdout(f2):
                    ret2 = main(["autopilot", "--no-git-hooks", "--json"])
                self.assertEqual(ret2, 0)

                f3 = io.StringIO()
                with redirect_stdout(f3):
                    ret3 = main(["setup", "--no-git-hooks", "--json"])
                self.assertEqual(ret3, 0)
            finally:
                os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()
