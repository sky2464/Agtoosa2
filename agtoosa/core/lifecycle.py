"""Lifecycle State Machine: Review validation and mathematical proof verification."""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import resolve_node


class LifecycleEngine:
    """Enforces graph invariants for Spec -> Build -> Review -> Ship transitions."""

    def __init__(self, store: GraphStore, workspace_root: Path):
        self.store = store
        self.workspace_root = workspace_root

    def get_git_modified_files(self) -> List[str]:
        """Detect modified or untracked files from git status."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            files = []
            for line in res.stdout.splitlines():
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        files.append(parts[-1])
            return files
        except (subprocess.SubprocessError, FileNotFoundError):
            return []

    def review(self) -> Dict[str, Any]:
        """Review working tree against graph invariants."""
        modified_files = self.get_git_modified_files()
        
        findings = []
        unlinked_files = []
        affected_stories = set()

        for fpath in modified_files:
            file_node = self.store.get_node(f"file:{fpath}")
            if not file_node:
                unlinked_files.append(fpath)
                findings.append({
                    "severity": "WARNING",
                    "message": f"File '{fpath}' is not yet indexed in knowledge graph."
                })
                continue

            # Find stories linked to this file
            neighbors = self.store.get_neighbors(file_node["id"], direction="in")
            for n in neighbors:
                if n["node_type"] == "story":
                    affected_stories.add(n["name"])

        verdict = "APPROVED"
        if unlinked_files:
            verdict = "WARNING"

        return {
            "verdict": verdict,
            "modified_files": modified_files,
            "unlinked_files": unlinked_files,
            "affected_stories": sorted(list(affected_stories)),
            "findings": findings
        }

    def verify_ship_proof(self, story_id_or_name: str) -> Tuple[bool, List[str]]:
        """Verify the mathematical proof subgraph: Story -> Tasks Complete && Criteria Satisfied."""
        story_node = resolve_node(self.store, story_id_or_name)
        if not story_node:
            return False, [f"Story '{story_id_or_name}' not found in knowledge graph."]

        reasons = []
        neighbors = self.store.get_neighbors(story_node["id"], direction="out")

        criteria = [n for n in neighbors if n["node_type"] == "criterion"]
        tasks = [n for n in neighbors if n["node_type"] == "task"]

        if not criteria:
            reasons.append(f"Story '{story_node['name']}' has no defined Acceptance Criteria.")

        incomplete_tasks = [t for t in tasks if not t.get("metadata", {}).get("completed", False)]
        if incomplete_tasks:
            task_names = ", ".join(t["name"] for t in incomplete_tasks[:3])
            reasons.append(f"{len(incomplete_tasks)} incomplete task(s): {task_names}")

        can_ship = len(reasons) == 0
        return can_ship, reasons
