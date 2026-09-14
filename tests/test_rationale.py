"""Tests for DEV-047: Source rationale and decision provenance extractor."""

import tempfile
from pathlib import Path
from agtoosa.parser.rationale import extract_comment_rationale, rationale_to_graph_entities
from agtoosa.core.model import EdgeType


def test_extract_comment_rationale_python():
    """AC-22: Rationale binds to the correct scoped symbol or stays at file span."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "service.py"
        code_file.write_text(
            "# WHY: We use SQLite FTS5 for zero-dependency sub-second search per ADR-001\n"
            "class Engine:\n"
            "    # HACK: Workaround for SQLite busy timeout under concurrent writers\n"
            "    def connect(self):\n"
            "        pass\n"
            "\n"
            "# NOTE: Module-level unbindable note regarding POSIX signal handling\n"
        )

        spans = [
            {"id": "func:Engine.connect", "start_line": 3, "end_line": 5}
        ]

        rationales = extract_comment_rationale(code_file, root, spans)
        assert len(rationales) == 3

        # First rationale: top-level (no enclosing symbol span)
        assert rationales[0].marker_type == "WHY"
        assert rationales[0].enclosing_symbol_id is None
        assert "ADR-001" in rationales[0].citations

        # Second rationale: bound to Engine.connect
        assert rationales[1].marker_type == "HACK"
        assert rationales[1].enclosing_symbol_id == "func:Engine.connect"

        # Third rationale: module-level span
        assert rationales[2].marker_type == "NOTE"
        assert rationales[2].enclosing_symbol_id is None


def test_redaction_in_comment_rationale():
    """AC-23: Rationale is redacted if sensitive tokens appear in comments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "auth.py"
        code_file.write_text(
            "# NOTE: Using temporary token ghp_1234567890abcdefghijklmnopqrstuvwxyz for test\n"
        )
        rationales = extract_comment_rationale(code_file, root)
        assert len(rationales) == 1
        assert "ghp_" not in rationales[0].content
        assert "[REDACTED_" in rationales[0].content


def test_rationale_to_graph_entities():
    """AC-23: Rationale nodes link to enclosing target and cited ADRs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "db.py"
        code_file.write_text(
            "# ASSUMPTION: Database schema conforms to DEV-040 specification\n"
            "def init_db():\n"
            "    pass\n"
        )
        spans = [{"id": "func:init_db", "start_line": 2, "end_line": 3}]
        rationales = extract_comment_rationale(code_file, root, spans)
        nodes, edges = rationale_to_graph_entities(rationales)

        assert len(nodes) == 1
        assert nodes[0].id.startswith("rationale:db.py")
        assert len(edges) == 2  # 1 to target symbol, 1 to cited DEV-040 doc
        edge_types = [e.edge_type for e in edges]
        assert EdgeType.REFERENCES in edge_types
        assert EdgeType.EVIDENCED_BY in edge_types
