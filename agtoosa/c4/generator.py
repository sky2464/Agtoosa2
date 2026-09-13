"""C4 Architecture-as-Code Synthesizer Engine (DEV-028).

Extracts and synthesizes hierarchical C4 Architecture diagrams:
- Level 1: System Context
- Level 2: Container
- Level 3: Component
Directly from the Agtoosa knowledge graph in Mermaid C4, PlantUML C4, and Structurizr DSL.
"""

from __future__ import annotations
from enum import Enum
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import NodeType, EdgeType
from agtoosa.graph.store import GraphStore


class C4Level(str, Enum):
    CONTEXT = "context"
    CONTAINER = "container"
    COMPONENT = "component"


class C4Format(str, Enum):
    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    STRUCTURIZR = "structurizr"


def _sanitize_id(name: str) -> str:
    """Sanitize string for identifier in Mermaid / PlantUML / Structurizr."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
    if clean and clean[0].isdigit():
        clean = f"elem_{clean}"
    return clean or "element"


class C4DiagramGenerator:
    """Generates C4 Architecture-as-Code diagrams across Level 1, 2, and 3."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()

    def generate(
        self,
        level: C4Level | str = C4Level.CONTAINER,
        format_type: C4Format | str = C4Format.MERMAID,
        title: Optional[str] = None
    ) -> str:
        """Generate C4 diagram for the specified level and format."""
        lvl = C4Level(level.lower()) if isinstance(level, str) else level
        fmt = C4Format(format_type.lower()) if isinstance(format_type, str) else format_type

        if fmt == C4Format.MERMAID:
            return self._to_mermaid(lvl, title)
        elif fmt == C4Format.PLANTUML:
            return self._to_plantuml(lvl, title)
        elif fmt == C4Format.STRUCTURIZR:
            return self._to_structurizr(lvl, title)
        else:
            return self._to_mermaid(lvl, title)

    # --------------------------------------------------------------------------
    # MERMAID C4 RENDERER
    # --------------------------------------------------------------------------

    def _to_mermaid(self, level: C4Level, title: Optional[str] = None) -> str:
        lines: List[str] = []

        if level == C4Level.CONTEXT:
            diag_title = title or "System Context Diagram for Agtoosa Knowledge Engine"
            lines.append("C4Context")
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Person(developer, "Developer / Engineer", "Writes code, inspects architecture, and ships features")')
            lines.append('Person(ai_agent, "AI Coding Assistant", "Uses MCP tools for bounded context, blast radius, and refactoring")')
            lines.append('')
            lines.append('Enterprise_Boundary(b0, "Local Engineering Environment") {')
            lines.append('    System(agtoosa, "Agtoosa Knowledge Engine", "Autonomous software architecture knowledge engine, AST graph storage, and review intelligence")')
            lines.append('}')
            lines.append('')
            lines.append('System_Ext(github, "GitHub / Git Remote", "Houses repositories, PR diffs, CI/CD actions, and git hooks")')

            # Add federated repos if any exist
            fed_repos = self.store.get_federated_repos()
            for fed in fed_repos:
                fid = _sanitize_id(f"fed_{fed['name']}")
                lines.append(f'System_Ext({fid}, "Federated Repo: {fed["name"]}", "Remote service contracts and dependency graphs")')

            # Add external services discovered from telemetry traces
            services = self._get_services()
            for s in services[:5]:
                sid = _sanitize_id(f"svc_{s['name']}")
                lines.append(f'System_Ext({sid}, "{s["name"]}", "Distributed runtime microservice")')

            lines.append('')
            lines.append('Rel(developer, agtoosa, "Invokes CLI commands and explores Studio", "CLI / HTTP")')
            lines.append('Rel(developer, github, "Pushes commits and opens PRs", "Git")')
            lines.append('Rel(ai_agent, agtoosa, "Queries symbol context and blast radius", "MCP JSON-RPC")')
            lines.append('Rel(agtoosa, github, "Analyzes PR blast radius and posts sticky review comments", "REST API")')

            for fed in fed_repos:
                fid = _sanitize_id(f"fed_{fed['name']}")
                lines.append(f'Rel(agtoosa, {fid}, "Synchronizes API schemas & cross-repo contracts", "GraphQL / OpenAPI / Proto")')

            for s in services[:5]:
                sid = _sanitize_id(f"svc_{s['name']}")
                lines.append(f'Rel(agtoosa, {sid}, "Traces network RPC calls & latency percentiles", "OpenTelemetry OTLP")')

        elif level == C4Level.CONTAINER:
            diag_title = title or "Container Diagram for Agtoosa Architecture"
            lines.append("C4Container")
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Person(developer, "Developer", "Uses CLI and Agtoosa Studio")')
            lines.append('Person(ai_agent, "AI Assistant", "Cursor, Windsurf, Claude Code via MCP")')
            lines.append('')
            lines.append('System_Boundary(c1, "Agtoosa Knowledge Engine") {')
            lines.append('    Container(cli, "CLI Subsystem", "Python 3.11+ / argparse", "Unified command-line interface for indexing, reviews, refactoring, and CI gates")')
            lines.append('    Container(mcp, "Native MCP Server", "Python / JSON-RPC 2.0 stdio", "Serves semantic symbol context, blast radius, and tools to AI agents")')
            lines.append('    Container(studio, "Agtoosa Studio Server", "Python HTTP / Vanilla ES Modules", "Interactive architecture explorer and 2-way refactoring UI")')
            lines.append('    ContainerDb(db, "Knowledge Graph Storage", "SQLite / FTS5 Inverted Index", "Transactional persistence for nodes, edges, telemetry, and embeddings")')
            lines.append('}')
            lines.append('')

            # Add discovered topics/queues if any
            topics = self._get_topics()
            for t in topics[:4]:
                tid = _sanitize_id(f"top_{t['name']}")
                lines.append(f'ContainerQueue({tid}, "{t["name"]}", "{t.get("broker", "Queue").upper()}", "Asynchronous event stream")')

            # Add discovered services from traces
            services = self._get_services()
            for s in services[:5]:
                sid = _sanitize_id(f"svc_{s['name']}")
                lines.append(f'Container({sid}, "{s["name"]}", "Service Runtime", "Discovered via OpenTelemetry traces")')

            lines.append('')
            lines.append('Rel(developer, cli, "Runs agtoosa graph, review, refactor", "Terminal")')
            lines.append('Rel(developer, studio, "Views architecture and triggers safe pruning", "HTTP :8080")')
            lines.append('Rel(ai_agent, mcp, "Queries symbols and blast radius", "stdio")')
            lines.append('Rel(cli, db, "Indexes AST and writes graph entities", "SQLite WAL")')
            lines.append('Rel(mcp, db, "Reads symbol context and blast radius", "SQLite WAL")')
            lines.append('Rel(studio, db, "Fetches graph datasets and executes refactorings", "SQLite WAL")')

            for t in topics[:4]:
                tid = _sanitize_id(f"top_{t['name']}")
                lines.append(f'Rel(cli, {tid}, "Traces pub/sub lineage", "Parser Lineage")')

            # Add network edges between services if present
            net_edges = self._get_network_edges()
            for ne in net_edges[:6]:
                s_name = ne["source_id"].replace("service:", "").replace("endpoint:", "")
                t_name = ne["target_id"].replace("service:", "").replace("endpoint:", "")
                sid = _sanitize_id(f"svc_{s_name}")
                tid = _sanitize_id(f"svc_{t_name}")
                calls = ne.get("call_count", 0)
                p95 = ne.get("p95_duration_ms", 0.0)
                lines.append(f'Rel({sid}, {tid}, "Network Calls ({calls} calls, p95: {p95:.1f}ms)", "HTTP / gRPC")')

        elif level == C4Level.COMPONENT:
            diag_title = title or "Component Diagram for Agtoosa Knowledge Engine Core"
            lines.append("C4Component")
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Container_Boundary(core, "Agtoosa Core Processing Engine") {')
            lines.append('    Component(parser, "AST Parser Subsystem", "Python / AST & Framework Extractors", "Parses polyglot ASTs, framework routes (FastAPI/Express), and event topics")')
            lines.append('    Component(compiler, "Context Compiler", "Python / Graph RAG", "Compiles bounded prompt packs and evidence proof graphs")')
            lines.append('    Component(lifecycle, "Lifecycle & Guard Engine", "Python", "Enforces story criteria, pre-push drift invariants, and PR review bot")')
            lines.append('    Component(refactor, "Autonomous Refactor Engine", "Python / AST Rewriter", "Executes automated dead code pruning and cyclic dependency decoupling")')
            lines.append('    Component(observability, "Observability & Trace Ingester", "Python / OTLP Parser", "Ingests OpenTelemetry traces and computes dynamic service topologies")')
            lines.append('}')
            lines.append('')
            lines.append('ContainerDb(db, "SQLite Graph Store", "SQLite / FTS5", "Local transactional graph database")')
            lines.append('')
            lines.append('Rel(parser, db, "Writes AST nodes and dependency edges", "insert_batch")')
            lines.append('Rel(compiler, db, "Traverses upstream/downstream subgraphs", "SQL / FTS5")')
            lines.append('Rel(lifecycle, db, "Validates invariants and drift rules", "SQL CTE")')
            lines.append('Rel(refactor, db, "Queries dead code candidates and cycles", "MetricsEngine")')
            lines.append('Rel(observability, db, "Stores runtime telemetry & service topology", "insert_batch")')

        return '\n'.join(lines)

    # --------------------------------------------------------------------------
    # PLANTUML C4 RENDERER
    # --------------------------------------------------------------------------

    def _to_plantuml(self, level: C4Level, title: Optional[str] = None) -> str:
        lines: List[str] = ['@startuml']
        lines.append('!include <C4/C4_Context>')
        lines.append('!include <C4/C4_Container>')
        lines.append('!include <C4/C4_Component>')
        lines.append('')

        if level == C4Level.CONTEXT:
            diag_title = title or "System Context Diagram for Agtoosa Knowledge Engine"
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Person(developer, "Developer / Engineer", "Writes code and inspects architecture")')
            lines.append('Person(ai_agent, "AI Assistant", "Interacts via MCP protocol")')
            lines.append('System(agtoosa, "Agtoosa Knowledge Engine", "Autonomous software architecture knowledge engine")')
            lines.append('System_Ext(github, "GitHub / Git Remote", "Houses repos, PRs, and CI workflows")')
            lines.append('')
            lines.append('Rel(developer, agtoosa, "Runs commands and views Studio", "CLI / HTTP")')
            lines.append('Rel(ai_agent, agtoosa, "Queries symbol context", "MCP stdio")')
            lines.append('Rel(agtoosa, github, "Reviews PR blast radius", "REST API")')

        elif level == C4Level.CONTAINER:
            diag_title = title or "Container Diagram for Agtoosa Architecture"
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Person(developer, "Developer", "Uses CLI and Studio")')
            lines.append('Person(ai_agent, "AI Assistant", "Cursor / Windsurf / Claude Code")')
            lines.append('')
            lines.append('System_Boundary(c1, "Agtoosa Knowledge Engine") {')
            lines.append('    Container(cli, "CLI Subsystem", "Python 3.11+", "Unified command dispatcher")')
            lines.append('    Container(mcp, "Native MCP Server", "Python JSON-RPC", "MCP protocol stdio server")')
            lines.append('    Container(studio, "Agtoosa Studio", "Python / ES Modules", "Interactive architecture visualizer")')
            lines.append('    ContainerDb(db, "Knowledge Graph DB", "SQLite / FTS5", "Stores AST nodes, edges, and telemetry")')
            lines.append('}')
            lines.append('')
            lines.append('Rel(developer, cli, "Executes commands")')
            lines.append('Rel(developer, studio, "Explores architecture", "HTTP :8080")')
            lines.append('Rel(ai_agent, mcp, "Queries symbol context", "stdio")')
            lines.append('Rel(cli, db, "Writes AST nodes")')
            lines.append('Rel(mcp, db, "Queries graph")')
            lines.append('Rel(studio, db, "Polls graph data")')

        elif level == C4Level.COMPONENT:
            diag_title = title or "Component Diagram for Agtoosa Core"
            lines.append(f'title {diag_title}')
            lines.append('')
            lines.append('Container_Boundary(core, "Agtoosa Core Processing Engine") {')
            lines.append('    Component(parser, "AST Parser Subsystem", "Python", "Parses polyglot ASTs and routes")')
            lines.append('    Component(compiler, "Context Compiler", "Python", "Compiles prompt packs")')
            lines.append('    Component(lifecycle, "Lifecycle & Guard Engine", "Python", "Enforces architectural drift rules")')
            lines.append('    Component(refactor, "Refactor Engine", "Python", "Autonomous code pruning and decoupling")')
            lines.append('    Component(observability, "Trace Ingester", "Python", "Reconstructs distributed service topology")')
            lines.append('}')
            lines.append('')
            lines.append('ContainerDb(db, "SQLite Graph Store", "SQLite", "Local graph database")')
            lines.append('')
            lines.append('Rel(parser, db, "Writes entities")')
            lines.append('Rel(compiler, db, "Reads context")')
            lines.append('Rel(lifecycle, db, "Audits drift")')
            lines.append('Rel(refactor, db, "Applies blueprints")')
            lines.append('Rel(observability, db, "Persists service topology")')

        lines.append('')
        lines.append('@enduml')
        return '\n'.join(lines)

    # --------------------------------------------------------------------------
    # STRUCTURIZR DSL RENDERER
    # --------------------------------------------------------------------------

    def _to_structurizr(self, level: C4Level, title: Optional[str] = None) -> str:
        diag_title = title or "Agtoosa Architecture-as-Code"
        lines: List[str] = [
            f'workspace "{diag_title}" "Autonomous Software Architecture Knowledge Engine" {{',
            '    model {',
            '        developer = person "Developer" "Writes code and inspects architecture"',
            '        aiAgent = person "AI Assistant" "Interacts via Model Context Protocol"',
            '',
            '        agtoosa = softwareSystem "Agtoosa Knowledge Engine" "Knowledge graph, architectural intelligence, and refactoring" {',
            '            cli = container "CLI Subsystem" "Command line entrypoint" "Python 3.11+"',
            '            mcp = container "Native MCP Server" "Serves AI assistants" "Python JSON-RPC"',
            '            studio = container "Agtoosa Studio" "Interactive visualizer" "Python / Web"',
            '            db = container "Knowledge Graph Storage" "Stores AST nodes, edges, telemetry" "SQLite FTS5" "Database"',
            '        }',
            '',
            '        github = softwareSystem "GitHub" "Source repository and CI/CD actions" "External"',
            '',
            '        developer -> cli "Executes commands"',
            '        developer -> studio "Explores architecture"',
            '        developer -> github "Pushes commits and opens PRs"',
            '        aiAgent -> mcp "Queries symbol context and blast radius"',
            '        cli -> db "Writes AST and telemetry entities"',
            '        mcp -> db "Queries symbol context"',
            '        studio -> db "Reads graph datasets"',
            '        cli -> github "Posts PR review blast radius comments"',
            '    }',
            '',
            '    views {',
            '        systemContext agtoosa "SystemContext" {',
            '            include *',
            '            autoLayout',
            '        }',
            '        container agtoosa "Containers" {',
            '            include *',
            '            autoLayout',
            '        }',
            '        styles {',
            '            element "Software System" {',
            '                background #10b981',
            '                color #ffffff',
            '            }',
            '            element "External" {',
            '                background #64748b',
            '                color #ffffff',
            '            }',
            '            element "Database" {',
            '                shape Cylinder',
            '            }',
            '        }',
            '    }',
            '}'
        ]
        return '\n'.join(lines)

    # --------------------------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------------------------

    def _get_services(self) -> List[Dict[str, Any]]:
        nodes = self.store.get_all_nodes()
        return [n for n in nodes if n.get("node_type") == "service"]

    def _get_topics(self) -> List[Dict[str, Any]]:
        nodes = self.store.get_all_nodes()
        return [n for n in nodes if n.get("node_type") == "topic"]

    def _get_network_edges(self) -> List[Dict[str, Any]]:
        with self.store._get_connection() as conn:
            rows = conn.execute(
                "SELECT source_id, target_id, metadata_json FROM edges WHERE edge_type = 'network_calls';"
            ).fetchall()
        import json
        edges = []
        for r in rows:
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            edges.append({
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "call_count": meta.get("call_count", 0),
                "p95_duration_ms": meta.get("p95_duration_ms", 0.0)
            })
        return edges
