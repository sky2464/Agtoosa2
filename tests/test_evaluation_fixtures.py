"""Tests for DEV-046: Multilingual evaluation fixtures and scoped ambiguity ground-truth."""

from pathlib import Path
from agtoosa.parser.capabilities import CAPABILITY_REGISTRY
from agtoosa.parser.python_parser import PythonASTParser
from agtoosa.parser.js_ts_parser import JavaScriptTypeScriptParser
from agtoosa.parser.polyglot_parser import PolyglotParser
from agtoosa.parser.rationale import extract_comment_rationale


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "trusted_graph"


def test_python_scope_fixture():
    """Verify ground truth on Python scoped fixture."""
    fixture = FIXTURES_DIR / "python" / "scope_fixture.py"
    assert fixture.exists()

    cap = CAPABILITY_REGISTRY.find_capability_for_file(fixture)
    assert cap.family_id == "python"

    parser = PythonASTParser()
    nodes, edges = parser.parse(fixture, FIXTURES_DIR)

    # Must find classes UserService, OrderService
    class_names = [n.name for n in nodes if n.node_type == "class"]
    assert "UserService" in class_names
    assert "OrderService" in class_names

    # Ghost function in string literal must NEVER be extracted as an AST node
    func_names = [n.name for n in nodes if n.node_type == "function"]
    assert "ghost_function" not in func_names

    # Extract rationales
    rationales = extract_comment_rationale(fixture, FIXTURES_DIR)
    assert any(r.marker_type == "WHY" for r in rationales)
    assert any(r.marker_type == "NOTE" for r in rationales)


def test_typescript_scope_fixture():
    """Verify ground truth on TypeScript scoped fixture."""
    fixture = FIXTURES_DIR / "ts_js" / "scope_fixture.ts"
    assert fixture.exists()

    cap = CAPABILITY_REGISTRY.find_capability_for_file(fixture)
    assert cap.family_id == "javascript_typescript"

    parser = JavaScriptTypeScriptParser()
    nodes, edges = parser.parse(fixture, FIXTURES_DIR)

    class_names = [n.name for n in nodes if n.node_type == "class"]
    assert "AuthService" in class_names
    assert "PaymentGateway" in class_names

    func_names = [n.name for n in nodes if n.node_type == "function"]
    assert "processBatch" in func_names


def test_go_scope_fixture():
    """Verify ground truth on Go receiver method fixture."""
    fixture = FIXTURES_DIR / "go" / "scope_fixture.go"
    assert fixture.exists()

    cap = CAPABILITY_REGISTRY.find_capability_for_file(fixture)
    assert cap.family_id == "go"

    parser = PolyglotParser()
    nodes, edges = parser.parse(fixture, FIXTURES_DIR)

    # Structs User and Order
    struct_names = [n.name for n in nodes if n.node_type == "class"]
    assert "User" in struct_names
    assert "Order" in struct_names
