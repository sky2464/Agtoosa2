"""Universal AI Agent Workflow Enforcement & Instruction Injector (DEV-058).

Ensures all future AI development across Claude Code, Cursor, Antigravity, Copilot,
and Windsurf adheres to Agtoosa2 graph synchronization, boundary reviews, and quality gates.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional

RULES_START_TAG = "<!-- AGTOOSA_AGENT_RULES_START -->"
RULES_END_TAG = "<!-- AGTOOSA_AGENT_RULES_END -->"

AGENT_INSTRUCTIONS_BODY = f"""{RULES_START_TAG}
## Architectural Guardrails & Graph-Native Workflow (Agtoosa2)

This repository is governed by Agtoosa2 architectural knowledge graph and quality gates.
All AI agents working in this workspace must adhere to the following workflow:

1. **Pre-Flight Architecture Discovery**:
   Before modifying existing modules, classes, or dependencies, query the codebase topology and blast radius:
   ```bash
   agtoosa query "<feature_or_symbol>" --budget 1500
   ```

2. **Continuous Graph Synchronization**:
   Whenever you add, modify, or delete files, refresh the local knowledge graph:
   ```bash
   agtoosa graph build
   ```

3. **Architecture Quality Gate & Boundary Verification**:
   Before completing tasks or committing changes, verify architectural invariants (zero cycles, strict layer boundaries):
   ```bash
   agtoosa review
   ```
   Do not commit code if `agtoosa review` reports circular dependencies or unauthorized layer crossing.

4. **Emergency Rollback**:
   If an automated refactoring or migration causes architectural regressions, invoke:
   ```bash
   agtoosa refactor rollback
   ```
{RULES_END_TAG}"""

CURSOR_MDC_CONTENT = f"""---
description: Agtoosa2 Graph-Native Architectural Guardrails
globs: *
---
{AGENT_INSTRUCTIONS_BODY}
"""


class AgentWorkflowEnforcer:
    """Installs and non-destructively manages Agtoosa instructions in agent rule files."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def is_enforced(self) -> bool:
        """Return True if at least one primary agent rule file has Agtoosa rules installed."""
        primary_files = [
            self.workspace_root / "AGENTS.md",
            self.workspace_root / "CLAUDE.md",
            self.workspace_root / ".cursor" / "rules" / "agtoosa.mdc",
        ]
        for f in primary_files:
            if f.exists():
                text = f.read_text(encoding="utf-8", errors="ignore")
                if RULES_START_TAG in text:
                    return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Inspect workspace agent rule files and report enforcement status."""
        targets = {
            "AGENTS.md": self.workspace_root / "AGENTS.md",
            "CLAUDE.md": self.workspace_root / "CLAUDE.md",
            "Cursor (.cursor/rules/agtoosa.mdc)": self.workspace_root / ".cursor" / "rules" / "agtoosa.mdc",
            "Windsurf (.windsurfrules)": self.workspace_root / ".windsurfrules",
            "GitHub Copilot (.github/copilot-instructions.md)": self.workspace_root / ".github" / "copilot-instructions.md",
        }
        report: Dict[str, bool] = {}
        for name, p in targets.items():
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="ignore")
                report[name] = RULES_START_TAG in text
            else:
                report[name] = False

        return {
            "is_enforced": any(report.values()),
            "files": report
        }

    @staticmethod
    def inject_or_update(
        file_path: Path,
        rules_block: str,
        default_header: str = ""
    ) -> bool:
        """Inject or non-destructively update delimited rules block in target file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            initial_content = f"{default_header}\n\n{rules_block}\n" if default_header else f"{rules_block}\n"
            file_path.write_text(initial_content.strip() + "\n", encoding="utf-8")
            return True

        content = file_path.read_text(encoding="utf-8", errors="ignore")

        # If existing block found, replace it precisely using exact boundary tags
        start_idx = content.find(RULES_START_TAG)
        end_idx = content.find(RULES_END_TAG)
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            full_end = end_idx + len(RULES_END_TAG)
            new_content = content[:start_idx] + rules_block + content[full_end:]
            file_path.write_text(new_content, encoding="utf-8")
            return True

        # Append to end if not present
        new_content = content.rstrip() + "\n\n" + rules_block + "\n"
        file_path.write_text(new_content, encoding="utf-8")
        return True

    def install_all(
        self,
        targets: Optional[List[str]] = None,
        with_git_hooks: bool = False,
    ) -> Dict[str, Any]:
        """Install or update Agtoosa governance instructions across agent targets."""
        target_list = [t.lower() for t in (targets or ["all"])]
        all_targets = "all" in target_list

        installed_files: List[str] = []

        # 1. AGENTS.md (Universal standard: Antigravity, Gemini CLI, Codex, Cursor)
        if all_targets or "agents" in target_list:
            p = self.workspace_root / "AGENTS.md"
            header = f"# Repository Guidelines ({self.workspace_root.name})"
            self.inject_or_update(p, AGENT_INSTRUCTIONS_BODY, default_header=header)
            installed_files.append("AGENTS.md")

        # 2. CLAUDE.md (Claude Code)
        if all_targets or "claude" in target_list:
            p = self.workspace_root / "CLAUDE.md"
            header = f"# Claude Guidelines ({self.workspace_root.name})"
            self.inject_or_update(p, AGENT_INSTRUCTIONS_BODY, default_header=header)
            installed_files.append("CLAUDE.md")

        # 3. Cursor MDC rule
        if all_targets or "cursor" in target_list:
            p = self.workspace_root / ".cursor" / "rules" / "agtoosa.mdc"
            self.inject_or_update(p, CURSOR_MDC_CONTENT)
            installed_files.append(".cursor/rules/agtoosa.mdc")

        # 4. Windsurf rules
        if all_targets or "windsurf" in target_list:
            p = self.workspace_root / ".windsurfrules"
            self.inject_or_update(p, AGENT_INSTRUCTIONS_BODY)
            installed_files.append(".windsurfrules")

        # 5. GitHub Copilot instructions
        if all_targets or "copilot" in target_list:
            p = self.workspace_root / ".github" / "copilot-instructions.md"
            header = "# GitHub Copilot Instructions"
            self.inject_or_update(p, AGENT_INSTRUCTIONS_BODY, default_header=header)
            installed_files.append(".github/copilot-instructions.md")

        return {
            "workspace": str(self.workspace_root),
            "installed_files": installed_files,
            "is_enforced": True
        }
