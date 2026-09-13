"""AST extractor for Python source files using standard library ast."""

import ast
from pathlib import Path
from typing import List, Tuple, Optional

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.parser.base import BaseParser


class PythonASTParser(BaseParser):
    """Parses Python source files into AST symbols and relationship edges."""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".py"

    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        rel_path = str(file_path.relative_to(workspace_root))
        file_node_id = f"file:{rel_path}"

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError:
            # Create a file node indicating parse error
            nodes.append(
                Node(
                    id=file_node_id,
                    name=file_path.name,
                    node_type=NodeType.FILE,
                    path=rel_path,
                    metadata={"parse_warning": "syntax_error"}
                )
            )
            return nodes, edges

        # File Node
        module_doc = ast.get_docstring(tree)
        nodes.append(
            Node(
                id=file_node_id,
                name=file_path.name,
                node_type=NodeType.FILE,
                path=rel_path,
                docstring=module_doc,
                metadata={"total_lines": len(source.splitlines())}
            )
        )

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.current_parent_id = file_node_id
                self.scope_prefix = rel_path.replace("/", ".").removesuffix(".py")

            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    import_id = f"import:{rel_path}:{alias.name}"
                    nodes.append(
                        Node(
                            id=import_id,
                            name=alias.name,
                            node_type=NodeType.IMPORT,
                            path=rel_path,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            metadata={"asname": alias.asname}
                        )
                    )
                    edges.append(
                        Edge(
                            source_id=file_node_id,
                            target_id=import_id,
                            edge_type=EdgeType.IMPORTS
                        )
                    )
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    full_name = f"{mod}.{alias.name}" if mod else alias.name
                    import_id = f"import:{rel_path}:{full_name}"
                    nodes.append(
                        Node(
                            id=import_id,
                            name=full_name,
                            node_type=NodeType.IMPORT,
                            path=rel_path,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            metadata={"module": mod, "name": alias.name, "asname": alias.asname}
                        )
                    )
                    edges.append(
                        Edge(
                            source_id=file_node_id,
                            target_id=import_id,
                            edge_type=EdgeType.IMPORTS
                        )
                    )
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef):
                class_id = f"class:{rel_path}:{node.name}"
                doc = ast.get_docstring(node)
                bases = [ast.unparse(b) for b in node.bases if hasattr(ast, "unparse")]

                nodes.append(
                    Node(
                        id=class_id,
                        name=node.name,
                        node_type=NodeType.CLASS,
                        path=rel_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        docstring=doc,
                        metadata={"bases": bases}
                    )
                )
                edges.append(
                    Edge(
                        source_id=self.current_parent_id,
                        target_id=class_id,
                        edge_type=EdgeType.CONTAINS
                    )
                )

                # Record base inheritance
                for base in bases:
                    edges.append(
                        Edge(
                            source_id=class_id,
                            target_id=f"type:{base}",
                            edge_type=EdgeType.INHERITS,
                            provenance="inferred"
                        )
                    )

                prev_parent = self.current_parent_id
                self.current_parent_id = class_id
                self.generic_visit(node)
                self.current_parent_id = prev_parent

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_function(node, is_async=True)

            def _handle_function(self, node, is_async=False):
                func_id = f"func:{rel_path}:{self.current_parent_id.split(':')[-1]}.{node.name}" if self.current_parent_id != file_node_id else f"func:{rel_path}:{node.name}"
                doc = ast.get_docstring(node)
                args = [a.arg for a in node.args.args]

                nodes.append(
                    Node(
                        id=func_id,
                        name=node.name,
                        node_type=NodeType.FUNCTION,
                        path=rel_path,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        docstring=doc,
                        metadata={"args": args, "is_async": is_async}
                    )
                )
                edges.append(
                    Edge(
                        source_id=self.current_parent_id,
                        target_id=func_id,
                        edge_type=EdgeType.CONTAINS
                    )
                )

                # Walk body to find function calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and hasattr(child.func, "id"):
                        callee_name = child.func.id
                        edges.append(
                            Edge(
                                source_id=func_id,
                                target_id=f"func_call:{callee_name}",
                                edge_type=EdgeType.CALLS,
                                provenance="inferred"
                            )
                        )

                prev_parent = self.current_parent_id
                self.current_parent_id = func_id
                self.generic_visit(node)
                self.current_parent_id = prev_parent

        visitor = Visitor()
        visitor.visit(tree)

        # Extract Framework Semantics (FastAPI routes, Depends DI, SQLAlchemy/Django ORM)
        from agtoosa.parser.frameworks import PythonFrameworkExtractor
        fw_nodes, fw_edges = PythonFrameworkExtractor.extract(source, rel_path, tree, file_node_id)
        nodes.extend(fw_nodes)
        edges.extend(fw_edges)

        return nodes, edges

