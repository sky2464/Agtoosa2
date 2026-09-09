"""Tests for Lifecycle and Context Compiler v2."""

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.core.context_compiler import ContextCompiler
from agtoosa.core.lifecycle import LifecycleEngine
from agtoosa.parser.doc_parser import MarkdownDocParser


class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_markdown_doc_parser(self):
        spec_file = self.root / "spec-DEV-099.md"
        spec_file.write_text(
            """# Spec: DEV-099 — Realtime Telemetry

- **AC-1 (Ubiquitous)**: System SHALL emit metrics every 5 seconds.
- **AC-2 (Event-Driven)**: WHEN error occurs, system SHALL emit an alert.

### Tasks
- [x] **Task 1.1**: Setup websocket emitter.
- [ ] **Task 1.2**: Implement buffer queue.
""",
            encoding="utf-8"
        )

        parser = MarkdownDocParser()
        self.assertTrue(parser.can_parse(spec_file))

        nodes, edges = parser.parse(spec_file, self.root)

        node_types = {n.node_type for n in nodes}
        self.assertIn(NodeType.STORY, node_types)
        self.assertIn(NodeType.CRITERION, node_types)
        self.assertIn(NodeType.TASK, node_types)

        story = next(n for n in nodes if n.node_type == NodeType.STORY)
        self.assertIn("DEV-099", story.id)

        crit_nodes = [n for n in nodes if n.node_type == NodeType.CRITERION]
        self.assertEqual(len(crit_nodes), 2)

        task_nodes = [n for n in nodes if n.node_type == NodeType.TASK]
        self.assertEqual(len(task_nodes), 2)
        task_1 = next(t for t in task_nodes if "Task_1.1" in t.id)
        self.assertTrue(task_1.metadata["completed"])
        task_2 = next(t for t in task_nodes if "Task_1.2" in t.id)
        self.assertFalse(task_2.metadata["completed"])

    def test_context_compiler(self):
        # Insert story and criteria
        nodes = [
            Node(id="story:DEV-042", name="DEV-042: Auth Service", node_type=NodeType.STORY, path="spec.md"),
            Node(id="criterion:DEV-042:AC-1", name="DEV-042 AC-1", node_type=NodeType.CRITERION, path="spec.md", docstring="User must log in"),
            Node(id="task:DEV-042:Task_1", name="DEV-042 Task 1", node_type=NodeType.TASK, path="spec.md", docstring="Create login handler", metadata={"completed": False}),
            Node(id="func:login_user", name="login_user", node_type=NodeType.FUNCTION, path="auth.py", docstring="Execute user login")
        ]
        edges = [
            Edge(source_id="story:DEV-042", target_id="criterion:DEV-042:AC-1", edge_type=EdgeType.DEFINES),
            Edge(source_id="story:DEV-042", target_id="task:DEV-042:Task_1", edge_type=EdgeType.CONTAINS)
        ]
        self.store.insert_batch(nodes, edges)

        compiler = ContextCompiler(self.store)
        pack = compiler.compile_context("DEV-042")

        self.assertIsNotNone(pack)
        self.assertIn("Agtoosa Context Pack: DEV-042: Auth Service", pack)
        self.assertIn("DEV-042 AC-1", pack)
        self.assertIn("Create login handler", pack)

    def test_lifecycle_proof_verification(self):
        # Incomplete story
        nodes = [
            Node(id="story:DEV-010", name="DEV-010: Payment", node_type=NodeType.STORY, path="spec.md"),
            Node(id="criterion:DEV-010:AC-1", name="AC-1", node_type=NodeType.CRITERION, path="spec.md"),
            Node(id="task:DEV-010:Task_1", name="Task 1", node_type=NodeType.TASK, path="spec.md", metadata={"completed": False})
        ]
        edges = [
            Edge(source_id="story:DEV-010", target_id="criterion:DEV-010:AC-1", edge_type=EdgeType.DEFINES),
            Edge(source_id="story:DEV-010", target_id="task:DEV-010:Task_1", edge_type=EdgeType.CONTAINS)
        ]
        self.store.insert_batch(nodes, edges)

        lifecycle = LifecycleEngine(self.store, self.root)
        can_ship, reasons = lifecycle.verify_ship_proof("DEV-010")
        self.assertFalse(can_ship)
        self.assertTrue(any("incomplete task" in r for r in reasons))

        # Mark task completed
        nodes_done = [
            Node(id="task:DEV-010:Task_1", name="Task 1", node_type=NodeType.TASK, path="spec.md", metadata={"completed": True})
        ]
        self.store.insert_batch(nodes_done, [])
        can_ship, reasons = lifecycle.verify_ship_proof("DEV-010")
        self.assertTrue(can_ship)
        self.assertEqual(len(reasons), 0)


if __name__ == "__main__":
    unittest.main()
