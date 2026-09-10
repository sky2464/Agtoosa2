"""Polyglot parser extracting symbols, structs, functions, and imports across multiple programming languages."""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Set

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.parser.base import BaseParser


class PolyglotParser(BaseParser):
    """Extracts symbols, definitions, and dependencies from Go, Rust, Java/Kotlin, C/C++, C#, SQL, and Dockerfile."""

    # Supported extensions and special filenames
    SUPPORTED_EXTENSIONS = {
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".c": "c_cpp",
        ".cpp": "c_cpp",
        ".cc": "c_cpp",
        ".cxx": "c_cpp",
        ".h": "c_cpp",
        ".hpp": "c_cpp",
        ".hxx": "c_cpp",
        ".cs": "csharp",
        ".sql": "sql",
    }

    # Go Regexes
    GO_PACKAGE_REGEX = re.compile(r"^\s*package\s+([a-zA-Z0-9_]+)", re.MULTILINE)
    GO_IMPORT_SINGLE_REGEX = re.compile(r'^\s*import\s+(?:[a-zA-Z0-9_.]+\s+)?"([^"]+)"', re.MULTILINE)
    GO_IMPORT_BLOCK_REGEX = re.compile(r'import\s*\((.*?)\)', re.DOTALL)
    GO_STRUCT_REGEX = re.compile(r'^\s*type\s+([A-Z][a-zA-Z0-9_]*)\s+struct\b', re.MULTILINE)
    GO_INTERFACE_REGEX = re.compile(r'^\s*type\s+([A-Z][a-zA-Z0-9_]*)\s+interface\b', re.MULTILINE)
    GO_FUNC_REGEX = re.compile(r'^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)

    # Rust Regexes
    RUST_USE_REGEX = re.compile(r'^\s*(?:pub\s+)?use\s+([^;]+);', re.MULTILINE)
    RUST_STRUCT_REGEX = re.compile(r'^\s*(?:pub(?:\([^)]+\))?\s+)?struct\s+([a-zA-Z0-9_]+)', re.MULTILINE)
    RUST_ENUM_REGEX = re.compile(r'^\s*(?:pub(?:\([^)]+\))?\s+)?enum\s+([a-zA-Z0-9_]+)', re.MULTILINE)
    RUST_TRAIT_REGEX = re.compile(r'^\s*(?:pub(?:\([^)]+\))?\s+)?trait\s+([a-zA-Z0-9_]+)', re.MULTILINE)
    RUST_FN_REGEX = re.compile(r'^\s*(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
    RUST_IMPL_REGEX = re.compile(r'^\s*impl(?:\s*<[^>]+>)?\s+(?:([a-zA-Z0-9_]+)\s+for\s+)?([a-zA-Z0-9_]+)', re.MULTILINE)

    # Java / Kotlin Regexes
    JAVA_IMPORT_REGEX = re.compile(r'^\s*import\s+(?:static\s+)?([a-zA-Z0-9_.*]+);', re.MULTILINE)
    KT_IMPORT_REGEX = re.compile(r'^\s*import\s+([a-zA-Z0-9_.*]+)', re.MULTILINE)
    JAVA_CLASS_REGEX = re.compile(
        r'^\s*(?:public|protected|private)?\s*(?:static)?\s*(?:abstract|final)?\s*(?:class|interface|enum|record)\s+([a-zA-Z0-9_]+)(?:\s+extends\s+([a-zA-Z0-9_.]+))?(?:\s+implements\s+([a-zA-Z0-9_.,\s]+))?',
        re.MULTILINE
    )
    KT_CLASS_REGEX = re.compile(
        r'^\s*(?:open|abstract|data|sealed|enum)?\s*(?:class|interface|object)\s+([a-zA-Z0-9_]+)(?:\s*:\s*([a-zA-Z0-9_.,\s()]+))?',
        re.MULTILINE
    )
    KT_FUN_REGEX = re.compile(r'^\s*(?:override|private|protected|public|internal)?\s*fun\s+(?:<[^>]+>\s*)?([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
    JAVA_METHOD_REGEX = re.compile(
        r'^\s*(?:public|protected|private)?\s*(?:static)?\s*(?:final|synchronized|abstract)?\s*[a-zA-Z0-9_<>,\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*\{',
        re.MULTILINE
    )

    # C / C++ Regexes
    CPP_INCLUDE_REGEX = re.compile(r'^\s*#include\s+["<]([^">]+)[">]', re.MULTILINE)
    CPP_CLASS_REGEX = re.compile(r'^\s*(?:class|struct)\s+([a-zA-Z0-9_]+)(?:\s*:\s*(?:public|protected|private)?\s*([a-zA-Z0-9_]+))?\s*\{', re.MULTILINE)
    CPP_FUNC_REGEX = re.compile(
        r'^\s*(?:inline|static|virtual|explicit)?\s*[a-zA-Z0-9_*&:<>]+\s+([a-zA-Z0-9_]+)\s*\([^;{)]*\)\s*(?:const)?\s*\{',
        re.MULTILINE
    )

    # C# Regexes
    CS_USING_REGEX = re.compile(r'^\s*using\s+(?:static\s+)?([a-zA-Z0-9_.]+);', re.MULTILINE)
    CS_CLASS_REGEX = re.compile(
        r'^\s*(?:public|protected|internal|private)?\s*(?:static|sealed|abstract|partial)?\s*(?:class|interface|struct|record)\s+([a-zA-Z0-9_]+)(?:\s*:\s*([a-zA-Z0-9_.,\s]+))?',
        re.MULTILINE
    )
    CS_METHOD_REGEX = re.compile(
        r'^\s*(?:public|protected|internal|private)?\s*(?:static|virtual|override|async)?\s*[a-zA-Z0-9_<>,\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^;{)]*\)\s*\{',
        re.MULTILINE
    )

    # SQL DDL Regexes
    SQL_CREATE_TABLE_REGEX = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:["`]?([a-zA-Z0-9_]+)["`]?\.)?["`]?([a-zA-Z0-9_]+)["`]?', re.IGNORECASE)
    SQL_CREATE_VIEW_REGEX = re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(?:["`]?([a-zA-Z0-9_]+)["`]?\.)?["`]?([a-zA-Z0-9_]+)["`]?', re.IGNORECASE)
    SQL_FOREIGN_KEY_REGEX = re.compile(r'REFERENCES\s+(?:["`]?([a-zA-Z0-9_]+)["`]?\.)?["`]?([a-zA-Z0-9_]+)["`]?', re.IGNORECASE)

    # Dockerfile Regexes
    DOCKER_FROM_REGEX = re.compile(r'^\s*FROM\s+([^\s]+)(?:\s+[aA][sS]\s+([^\s]+))?', re.MULTILINE)
    DOCKER_CMD_REGEX = re.compile(r'^\s*(?:ENTRYPOINT|CMD|EXPOSE|ENV)\s+(.+)', re.MULTILINE)

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            return True
        name = file_path.name.lower()
        if name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile"):
            return True
        return False

    def _get_language(self, file_path: Path) -> str:
        name = file_path.name.lower()
        if name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile"):
            return "dockerfile"
        return self.SUPPORTED_EXTENSIONS.get(file_path.suffix.lower(), "generic")

    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        rel_path = str(file_path.relative_to(workspace_root))
        file_node_id = f"file:{rel_path}"

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return nodes, edges

        lines = content.splitlines()
        lang = self._get_language(file_path)

        # File Node
        nodes.append(
            Node(
                id=file_node_id,
                name=file_path.name,
                node_type=NodeType.FILE,
                path=rel_path,
                metadata={"total_lines": len(lines), "language": lang}
            )
        )

        dispatch = {
            "go": self._parse_go,
            "rust": self._parse_rust,
            "java": self._parse_java,
            "kotlin": self._parse_kotlin,
            "c_cpp": self._parse_c_cpp,
            "csharp": self._parse_csharp,
            "sql": self._parse_sql,
            "dockerfile": self._parse_dockerfile,
        }

        handler = dispatch.get(lang)
        if handler:
            n, e = handler(content, rel_path, file_node_id)
            nodes.extend(n)
            edges.extend(e)

        return nodes, edges

    def _line_num(self, content: str, index: int) -> int:
        return content[:index].count("\n") + 1

    def _parse_go(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Package
        pkg_match = self.GO_PACKAGE_REGEX.search(content)
        package_name = pkg_match.group(1) if pkg_match else "main"

        # Single Imports
        for m in self.GO_IMPORT_SINGLE_REGEX.finditer(content):
            pkg = m.group(1)
            imp_id = f"import:{rel_path}:{pkg}"
            nodes.append(Node(id=imp_id, name=pkg, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Block Imports
        for b in self.GO_IMPORT_BLOCK_REGEX.finditer(content):
            block_text = b.group(1)
            for m in re.finditer(r'"([^"]+)"', block_text):
                pkg = m.group(1)
                imp_id = f"import:{rel_path}:{pkg}"
                nodes.append(Node(id=imp_id, name=pkg, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, b.start())))
                edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Structs
        for m in self.GO_STRUCT_REGEX.finditer(content):
            name = m.group(1)
            struct_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=struct_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "struct", "package": package_name}))
            edges.append(Edge(source_id=file_node_id, target_id=struct_id, edge_type=EdgeType.CONTAINS))

        # Interfaces
        for m in self.GO_INTERFACE_REGEX.finditer(content):
            name = m.group(1)
            iface_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=iface_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "interface", "package": package_name}))
            edges.append(Edge(source_id=file_node_id, target_id=iface_id, edge_type=EdgeType.CONTAINS))

        # Functions
        for m in self.GO_FUNC_REGEX.finditer(content):
            name = m.group(1)
            func_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=func_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"package": package_name}))
            edges.append(Edge(source_id=file_node_id, target_id=func_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges

    def _parse_rust(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Uses
        for m in self.RUST_USE_REGEX.finditer(content):
            path = m.group(1).strip()
            imp_id = f"import:{rel_path}:{path}"
            nodes.append(Node(id=imp_id, name=path, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Structs
        for m in self.RUST_STRUCT_REGEX.finditer(content):
            name = m.group(1)
            struct_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=struct_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "struct"}))
            edges.append(Edge(source_id=file_node_id, target_id=struct_id, edge_type=EdgeType.CONTAINS))

        # Enums
        for m in self.RUST_ENUM_REGEX.finditer(content):
            name = m.group(1)
            enum_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=enum_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "enum"}))
            edges.append(Edge(source_id=file_node_id, target_id=enum_id, edge_type=EdgeType.CONTAINS))

        # Traits
        for m in self.RUST_TRAIT_REGEX.finditer(content):
            name = m.group(1)
            trait_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=trait_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "trait"}))
            edges.append(Edge(source_id=file_node_id, target_id=trait_id, edge_type=EdgeType.CONTAINS))

        # Functions
        for m in self.RUST_FN_REGEX.finditer(content):
            name = m.group(1)
            func_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=func_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=func_id, edge_type=EdgeType.CONTAINS))

        # Impl Trait for Struct
        for m in self.RUST_IMPL_REGEX.finditer(content):
            trait_name = m.group(1)
            struct_name = m.group(2)
            if trait_name and struct_name:
                edges.append(Edge(
                    source_id=f"class:{rel_path}:{struct_name}",
                    target_id=f"class:{trait_name}",
                    edge_type=EdgeType.IMPLEMENTS,
                    provenance="unresolved"
                ))

        return nodes, edges

    def _parse_java(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Imports
        for m in self.JAVA_IMPORT_REGEX.finditer(content):
            imp = m.group(1)
            imp_id = f"import:{rel_path}:{imp}"
            nodes.append(Node(id=imp_id, name=imp, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Classes
        for m in self.JAVA_CLASS_REGEX.finditer(content):
            name = m.group(1)
            super_class = m.group(2)
            interfaces = m.group(3)
            class_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=class_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.CONTAINS))

            if super_class:
                edges.append(Edge(source_id=class_id, target_id=f"class:{super_class.strip()}", edge_type=EdgeType.INHERITS, provenance="unresolved"))
            if interfaces:
                for iface in interfaces.split(","):
                    iface_name = iface.strip()
                    if iface_name:
                        edges.append(Edge(source_id=class_id, target_id=f"class:{iface_name}", edge_type=EdgeType.IMPLEMENTS, provenance="unresolved"))

        # Methods
        for m in self.JAVA_METHOD_REGEX.finditer(content):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch"):
                continue
            method_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=method_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=method_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges

    def _parse_kotlin(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Imports
        for m in self.KT_IMPORT_REGEX.finditer(content):
            imp = m.group(1)
            imp_id = f"import:{rel_path}:{imp}"
            nodes.append(Node(id=imp_id, name=imp, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Classes
        for m in self.KT_CLASS_REGEX.finditer(content):
            name = m.group(1)
            parents = m.group(2)
            class_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=class_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.CONTAINS))

            if parents:
                for p in parents.split(","):
                    p_name = re.sub(r"\(.*?\)", "", p).strip()
                    if p_name:
                        edges.append(Edge(source_id=class_id, target_id=f"class:{p_name}", edge_type=EdgeType.INHERITS, provenance="unresolved"))

        # Functions
        for m in self.KT_FUN_REGEX.finditer(content):
            name = m.group(1)
            fun_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=fun_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=fun_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges

    def _parse_c_cpp(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Includes
        for m in self.CPP_INCLUDE_REGEX.finditer(content):
            header = m.group(1)
            inc_id = f"import:{rel_path}:{header}"
            nodes.append(Node(id=inc_id, name=header, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=inc_id, edge_type=EdgeType.IMPORTS))

        # Classes / Structs
        for m in self.CPP_CLASS_REGEX.finditer(content):
            name = m.group(1)
            parent = m.group(2)
            class_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=class_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.CONTAINS))

            if parent:
                edges.append(Edge(source_id=class_id, target_id=f"class:{parent.strip()}", edge_type=EdgeType.INHERITS, provenance="unresolved"))

        # Functions
        for m in self.CPP_FUNC_REGEX.finditer(content):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch"):
                continue
            func_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=func_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=func_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges

    def _parse_csharp(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Usings
        for m in self.CS_USING_REGEX.finditer(content):
            ns = m.group(1)
            imp_id = f"import:{rel_path}:{ns}"
            nodes.append(Node(id=imp_id, name=ns, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

        # Classes
        for m in self.CS_CLASS_REGEX.finditer(content):
            name = m.group(1)
            parents = m.group(2)
            class_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=class_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=class_id, edge_type=EdgeType.CONTAINS))

            if parents:
                for p in parents.split(","):
                    p_name = p.strip()
                    if p_name:
                        edges.append(Edge(source_id=class_id, target_id=f"class:{p_name}", edge_type=EdgeType.INHERITS, provenance="unresolved"))

        # Methods
        for m in self.CS_METHOD_REGEX.finditer(content):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch", "using", "lock"):
                continue
            func_id = f"func:{rel_path}:{name}"
            nodes.append(Node(id=func_id, name=name, node_type=NodeType.FUNCTION, path=rel_path, start_line=self._line_num(content, m.start())))
            edges.append(Edge(source_id=file_node_id, target_id=func_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges

    def _parse_sql(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # Tables
        for m in self.SQL_CREATE_TABLE_REGEX.finditer(content):
            schema = m.group(1)
            name = m.group(2)
            table_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=table_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "table", "schema": schema or "public"}))
            edges.append(Edge(source_id=file_node_id, target_id=table_id, edge_type=EdgeType.CONTAINS))

        # Views
        for m in self.SQL_CREATE_VIEW_REGEX.finditer(content):
            schema = m.group(1)
            name = m.group(2)
            view_id = f"class:{rel_path}:{name}"
            nodes.append(Node(id=view_id, name=name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "view", "schema": schema or "public"}))
            edges.append(Edge(source_id=file_node_id, target_id=view_id, edge_type=EdgeType.CONTAINS))

        # Foreign Key references
        for m in self.SQL_FOREIGN_KEY_REGEX.finditer(content):
            target_table = m.group(2)
            edges.append(Edge(
                source_id=file_node_id,
                target_id=f"class:{target_table}",
                edge_type=EdgeType.REFERENCES,
                provenance="unresolved"
            ))

        return nodes, edges

    def _parse_dockerfile(self, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        for m in self.DOCKER_FROM_REGEX.finditer(content):
            base_image = m.group(1)
            stage_name = m.group(2)
            imp_id = f"import:{rel_path}:{base_image}"
            nodes.append(Node(id=imp_id, name=base_image, node_type=NodeType.IMPORT, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"stage": stage_name or "base"}))
            edges.append(Edge(source_id=file_node_id, target_id=imp_id, edge_type=EdgeType.IMPORTS))

            if stage_name:
                stage_id = f"class:{rel_path}:{stage_name}"
                nodes.append(Node(id=stage_id, name=stage_name, node_type=NodeType.CLASS, path=rel_path, start_line=self._line_num(content, m.start()), metadata={"kind": "build_stage"}))
                edges.append(Edge(source_id=file_node_id, target_id=stage_id, edge_type=EdgeType.CONTAINS))

        return nodes, edges
