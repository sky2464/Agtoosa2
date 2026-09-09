"""Tests for AST parsers."""

import tempfile
import unittest
from pathlib import Path

from agtoosa.core.model import NodeType, EdgeType
from agtoosa.parser.python_parser import PythonASTParser
from agtoosa.parser.shell_parser import ShellScriptParser


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_python_parser(self):
        py_file = self.root / "sample.py"
        py_file.write_text(
            '''"""Sample module."""
import os
from math import sqrt

class Calculator:
    """A math calculator."""
    def add(self, a, b):
        return a + b

def run():
    calc = Calculator()
    return calc.add(1, 2)
''',
            encoding="utf-8"
        )

        parser = PythonASTParser()
        self.assertTrue(parser.can_parse(py_file))

        nodes, edges = parser.parse(py_file, self.root)

        # Check nodes
        node_types = [n.node_type for n in nodes]
        self.assertIn(NodeType.FILE, node_types)
        self.assertIn(NodeType.IMPORT, node_types)
        self.assertIn(NodeType.CLASS, node_types)
        self.assertIn(NodeType.FUNCTION, node_types)

        calc_node = next(n for n in nodes if n.name == "Calculator")
        self.assertEqual(calc_node.docstring, "A math calculator.")

        add_node = next(n for n in nodes if n.name == "add")
        self.assertIn("self", add_node.metadata["args"])

        # Check edges
        edge_types = [e.edge_type for e in edges]
        self.assertIn(EdgeType.IMPORTS, edge_types)
        self.assertIn(EdgeType.CONTAINS, edge_types)

    def test_shell_parser(self):
        sh_file = self.root / "deploy.sh"
        sh_file.write_text(
            '''#!/usr/bin/env bash
source config.env

setup_env() {
    echo "setting up"
}

function deploy() {
    setup_env
}
''',
            encoding="utf-8"
        )

        parser = ShellScriptParser()
        self.assertTrue(parser.can_parse(sh_file))

        nodes, edges = parser.parse(sh_file, self.root)

        func_names = [n.name for n in nodes if n.node_type == NodeType.FUNCTION]
        self.assertIn("setup_env", func_names)
        self.assertIn("deploy", func_names)

        import_names = [n.name for n in nodes if n.node_type == NodeType.IMPORT]
        self.assertIn("config.env", import_names)


if __name__ == "__main__":
    unittest.main()
