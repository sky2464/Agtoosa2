"""Native Model Context Protocol (MCP) Server for Agtoosa2."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agtoosa import __version__
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import explain_node, compute_impact
from agtoosa.core.context_compiler import ContextCompiler
from agtoosa.core.lifecycle import LifecycleEngine
from agtoosa.cli.graph_cmd import get_default_db_path


class MCPServer:
    """JSON-RPC 2.0 stdio server providing Agtoosa graph tools to AI assistants."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.db_path = get_default_db_path(workspace_root)
        self.store = GraphStore(self.db_path)
        self.compiler = ContextCompiler(self.store)
        self.lifecycle = LifecycleEngine(self.store, workspace_root)
        self.subscriptions: Set[str] = set()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "agtoosa_search_graph",
                "description": "Full-text search across all codebase symbols, docstrings, and specifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "limit": {"type": "integer", "description": "Maximum matches to return", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agtoosa_get_symbol",
                "description": "Inspect an exact symbol or file: definition, docstring, callers, and callees.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Symbol name or file path"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "agtoosa_query_impact",
                "description": "Calculate upstream blast radius (who calls or depends on target) before making edits.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Modified symbol or file"},
                        "depth": {"type": "integer", "description": "Max traversal depth", "default": 3},
                        "federated": {"type": "boolean", "description": "Include cross-repository callers and dependents", "default": True},
                        "production": {"type": "boolean", "description": "Weight blast radius with runtime traffic and error rates", "default": False}
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "agtoosa_list_federated_repos",
                "description": "List all registered federated repositories and their contract synchronization status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "agtoosa_sync_federation",
                "description": "Synchronize and ingest API schema contracts from registered federated repositories.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Specific repository alias or omit for all"}
                    }
                }
            },
            {
                "name": "agtoosa_get_task_context",
                "description": "Compile a bounded, high-signal prompt pack for an active task or story.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_or_story": {"type": "string", "description": "Story ID (e.g. DEV-001) or Task ID"},
                        "hybrid": {"type": "boolean", "description": "Enable Hybrid GraphRAG v2 with semantic vector embeddings", "default": True}
                    },
                    "required": ["task_or_story"]
                }
            },
            {
                "name": "agtoosa_hybrid_search",
                "description": "Hybrid semantic vector and full-text keyword search across codebase symbols using Reciprocal Rank Fusion (RRF).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "limit": {"type": "integer", "description": "Maximum matches to return", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agtoosa_verify_ship",
                "description": "Verify that all acceptance criteria and tasks for a story are complete.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID to verify"}
                    },
                    "required": ["story_id"]
                }
            },
            {
                "name": "agtoosa_watch_status",
                "description": "Get real-time continuous watcher status, graph stats, and pending drift findings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "agtoosa_check_monorepo_boundaries",
                "description": "Inspect monorepo package isolation boundaries, encapsulation leaks, circular package dependencies, and undeclared imports.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "strict": {"type": "boolean", "description": "Fail on warnings as well as errors", "default": False}
                    }
                }
            },
            {
                "name": "agtoosa_get_telemetry_heatmap",
                "description": "Retrieve runtime execution hotspot heatmaps (invocations, latency, error rates) across knowledge graph symbols.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "top": {"type": "integer", "description": "Top N hotspots to return", "default": 20}
                    }
                }
            },
            {
                "name": "agtoosa_suggest_cycle_decoupling",
                "description": "Analyze architectural cycles and generate dependency injection / protocol decoupling blueprints.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "agtoosa_detect_dead_code",
                "description": "Identify dead code / zombie symbols with zero callers and generate safe deletion blueprints.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "min_confidence": {"type": "string", "description": "Minimum confidence threshold: low, medium, or high", "default": "low"}
                    }
                }
            },
            {
                "name": "agtoosa_get_route_context",
                "description": "Retrieve comprehensive endpoint architecture: HTTP route, bound handler, injected DI services, and ORM tables.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "URL route path (e.g. /users or /orders/{id})"},
                        "method": {"type": "string", "description": "Optional HTTP verb (e.g. GET, POST)"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "agtoosa_get_di_graph",
                "description": "Retrieve dependency injection providers and consumers for a function, class, or service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Symbol or service name (e.g. get_db_session or UsersService)"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "agtoosa_get_event_lineage",
                "description": "Retrieve message queue topics, async publishers, subscribers, and event lineage across brokers (Kafka, RabbitMQ, Redis, Celery, BullMQ).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Optional topic name, channel name, or task queue filter"}
                    }
                }
            },
            {
                "name": "agtoosa_get_service_topology",
                "description": "Retrieve distributed runtime service topology, cross-service RPC/HTTP call paths, latency percentiles, and network bottlenecks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Optional service name to filter dependencies"}
                    }
                }
            },
            {
                "name": "agtoosa_get_c4_diagram",
                "description": "Generate hierarchical C4 Architecture-as-Code diagrams (Level 1: System Context, Level 2: Container, Level 3: Component) in Mermaid, PlantUML, or Structurizr DSL directly from the knowledge graph.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "description": "C4 level: context, container, or component", "default": "container"},
                        "format": {"type": "string", "description": "Diagram format: mermaid, plantuml, or structurizr", "default": "mermaid"},
                        "title": {"type": "string", "description": "Optional custom diagram title"}
                    }
                }
            },
            {
                "name": "agtoosa_auto_repair_pr",
                "description": "Autonomous AI repair agent diagnosing and synthesizing verified AST refactoring patches for circular dependencies, dead code, and architectural drift.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {"type": "boolean", "description": "Preview refactoring patch diff without modifying files", "default": True},
                        "base_ref": {"type": "string", "description": "Optional base git ref for diff evaluation"}
                    }
                }
            },
            {
                "name": "agtoosa_run_performance_benchmark",
                "description": "Execute continuous performance regression benchmarks on modified PR symbols or specific functions, comparing p95/p50 latency against baseline telemetry.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Optional symbol name, node ID, or path to benchmark"},
                        "base_ref": {"type": "string", "description": "Optional base git ref to benchmark modified symbols"},
                        "threshold_pct": {"type": "number", "description": "Regression threshold percentage (default: 10.0)", "default": 10.0},
                        "iterations": {"type": "integer", "description": "Benchmark iterations per symbol (default: 50)", "default": 50},
                        "save_baseline": {"type": "boolean", "description": "Whether to persist current measurements as new baseline", "default": False}
                    }
                }
            },
            {
                "name": "agtoosa_get_socratic_audit",
                "description": "Run active Socratic architecture audit detecting God nodes, cyclic hotspots, and unverified cross-modality couplings with 1-click refactoring blueprints (DEV-036).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "generate_blueprints": {"type": "boolean", "description": "Attach executable refactoring blueprints", "default": True}
                    }
                }
            },
            {
                "name": "agtoosa_budgeted_query",
                "description": "Execute token-budgeted topology query extracting high-centrality AST code skeletons within strict token limits (DEV-037).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or target symbol"},
                        "budget_tokens": {"type": "integer", "description": "Maximum token budget", "default": 1500},
                        "strategy": {"type": "string", "description": "Ranking strategy (hybrid, pagerank, bfs, dfs)", "default": "hybrid"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agtoosa_generate_attestation",
                "description": "Generate zero-knowledge architecture cryptographic attestation certificate with Merkle invariant proofs and blind commitments (DEV-038).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "signing_key": {"type": "string", "description": "Optional HMAC-SHA256 signing secret key"},
                        "salt": {"type": "string", "description": "Optional custom salt hex string"},
                        "include_leaves": {"type": "boolean", "description": "Include compliant leaf hashes in certificate", "default": False}
                    }
                }
            },
            {
                "name": "agtoosa_verify_attestation",
                "description": "Verify zero-knowledge architecture cryptographic attestation certificate (DEV-038).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "attestation": {"type": "object", "description": "Attestation JSON payload to verify"},
                        "signing_key": {"type": "string", "description": "Optional HMAC-SHA256 signing secret key"}
                    },
                    "required": ["attestation"]
                }
            },
            {
                "name": "agtoosa_synthesize_microservice",
                "description": "Autonomous cross-language microservice synthesis: generates gRPC (.proto), OpenAPI (3.0), and client/server adapters in Python, TypeScript, or Go (DEV-039).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string", "description": "Target service name"},
                        "target_lang": {"type": "string", "description": "Target language: python, typescript, go", "default": "python"},
                        "format": {"type": "string", "description": "Output format: proto, openapi, code, all", "default": "all"},
                        "output_dir": {"type": "string", "description": "Optional output directory to write artifacts to"}
                    }
                }
            },
            {
                "name": "agtoosa_list_specs",
                "description": "Inspect engineering specifications, criteria, and lifecycle tasks tracked in the Agtoosa knowledge graph (DEV-003).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Story ID (e.g. DEV-001) or 'all' to list all specifications", "default": "all"}
                    }
                }
            },
            {
                "name": "agtoosa_spectral_analysis",
                "description": "Execute algebraic and spectral graph theory analysis (DEV-052): graph Laplacian, Fiedler vector, Cheeger conductance bounds, spectral radius, minimum feedback arc set (FAS), transitive reduction, and Von Neumann graph entropy.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "description": "Spectral analysis mode: 'all', 'cut' (Fiedler & Cheeger), 'radius' (Perron-Frobenius), 'fas' (Minimum Feedback Arc Set), 'transitive' (Transitive reduction / Hasse)",
                            "default": "all"
                        }
                    }
                }
            },
            {
                "name": "agtoosa_submodular_context",
                "description": "Compile a provably bounded, near-optimal prompt pack using information-theoretic submodular knapsack optimization with (1 - 1/e) approximation ratio (DEV-053).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target story ID (e.g. DEV-001), task ID, or symbol name"
                        },
                        "budget_tokens": {
                            "type": "integer",
                            "description": "Token budget constraint for the prompt pack",
                            "default": 2000
                        }
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "agtoosa_curvature_audit",
                "description": "Audit discrete differential geometry invariants (DEV-054): Forman-Ricci edge curvature identifying architectural choke points and Gromov delta-hyperbolicity measuring tree-likeness.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "top": {
                            "type": "integer",
                            "description": "Top N fragile negative-curvature choke points to return",
                            "default": 20
                        },
                        "hyperbolic": {
                            "type": "boolean",
                            "description": "Compute Gromov 4-point delta-hyperbolicity",
                            "default": True
                        }
                    }
                }
            },
            {
                "name": "agtoosa_causal_effect",
                "description": "Evaluate Structural Causal Models and Pearl's Do-Calculus (DEV-055): identify back-door paths, minimal adjustment sets, and compute Average Causal Effect (ACE) to unconfound correlation from causation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Cause / treatment variable (symbol or node ID)"
                        },
                        "target": {
                            "type": "string",
                            "description": "Effect / outcome variable (symbol or node ID)"
                        },
                        "contingency_data": {
                            "type": "array",
                            "description": "Optional empirical observational records list: [{'var1': 0/1, 'var2': 0/1, ...}, ...]",
                            "items": {"type": "object"}
                        }
                    },
                    "required": ["source", "target"]
                }
            }
        ]


    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> str:
        if name == "agtoosa_search_graph":
            query = args.get("query", "")
            limit = args.get("limit", 10)
            results = self.store.query_fts(query, limit=limit)
            return json.dumps(results, indent=2)

        elif name == "agtoosa_hybrid_search":
            from agtoosa.graph.query import hybrid_search
            query = args.get("query", "")
            limit = args.get("limit", 10)
            results = hybrid_search(self.store, query, top_k=limit)
            return json.dumps(results, indent=2)

        elif name == "agtoosa_list_federated_repos":
            repos = self.store.get_federated_repos()
            return json.dumps(repos, indent=2)

        elif name == "agtoosa_sync_federation":
            from agtoosa.federation.manager import FederationManager
            mgr = FederationManager(self.store, self.workspace_root)
            repo_name = args.get("repo_name")
            try:
                res = mgr.sync_repository(repo_name) if repo_name else mgr.sync_all()
                return json.dumps(res, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)}, indent=2)

        elif name == "agtoosa_get_symbol":
            symbol = args.get("symbol", "")
            res = explain_node(self.store, symbol)
            return json.dumps(res or {"error": f"Symbol '{symbol}' not found"}, indent=2)

        elif name == "agtoosa_query_impact":
            target = args.get("target", "")
            raw_depth = args.get("depth", 3)
            federated = args.get("federated", True)
            production = args.get("production", False)
            try:
                depth = max(1, min(int(raw_depth), 5))
            except (ValueError, TypeError):
                depth = 3
            res = compute_impact(self.store, target, max_depth=depth, federated=federated, production=production)
            return json.dumps(res or {"error": f"Target '{target}' not found"}, indent=2)

        elif name == "agtoosa_get_task_context":
            target = args.get("task_or_story", "")
            hybrid = args.get("hybrid", True)
            pack = self.compiler.compile_context(target, hybrid=hybrid)
            return pack or f"Target '{target}' not found in knowledge graph."

        elif name == "agtoosa_verify_ship":
            story_id = args.get("story_id", "")
            can_ship, reasons = self.lifecycle.verify_ship_proof(story_id)
            return json.dumps({"approved": can_ship, "reasons": reasons}, indent=2)

        elif name == "agtoosa_check_monorepo_boundaries":
            from agtoosa.review.monorepo import MonorepoBoundaryEngine
            strict = args.get("strict", False)
            engine = MonorepoBoundaryEngine(self.workspace_root, store=self.store)
            report = engine.check_boundaries(strict=strict)
            return json.dumps(report.to_dict(), indent=2)

        elif name == "agtoosa_get_telemetry_heatmap":
            from agtoosa.observability.ingester import TelemetryIngester
            top_k = args.get("top", 20)
            ingester = TelemetryIngester(self.store, self.workspace_root)
            hotspots = ingester.compute_heatmaps(top_k=top_k)
            return json.dumps([h.to_dict() for h in hotspots], indent=2)

        elif name == "agtoosa_suggest_cycle_decoupling":
            from agtoosa.refactor.decoupler import CycleDecouplerEngine
            engine = CycleDecouplerEngine(self.store, self.workspace_root)
            report = engine.analyze_cycles()
            return json.dumps(report.to_dict(), indent=2)

        elif name == "agtoosa_detect_dead_code":
            from agtoosa.refactor.dead_code import DeadCodePruner
            min_confidence = args.get("min_confidence", "low")
            pruner = DeadCodePruner(self.store, self.workspace_root)
            report = pruner.analyze(min_confidence=min_confidence)
            return json.dumps(report.to_dict(), indent=2)

        elif name == "agtoosa_watch_status":
            stats = self.store.get_stats().to_dict()
            review_res = self.lifecycle.review()
            return json.dumps({
                "status": "active",
                "graph_stats": stats,
                "review_verdict": review_res.get("verdict"),
                "modified_files": review_res.get("modified_files", []),
                "findings": review_res.get("findings", [])
            }, indent=2)

        elif name == "agtoosa_get_route_context":
            from agtoosa.graph.query import query_routes
            req_path = args.get("path", "")
            req_method = args.get("method")
            all_routes = query_routes(self.store, method=req_method)
            matches = [r for r in all_routes if r["path"] == req_path or req_path in r["path"]]
            return json.dumps({"query_path": req_path, "matched_routes": matches}, indent=2)

        elif name == "agtoosa_get_di_graph":
            from agtoosa.graph.query import query_di
            symbol = args.get("symbol", "")
            di_res = query_di(self.store, symbol)
            return json.dumps(di_res, indent=2)

        elif name == "agtoosa_get_event_lineage":
            from agtoosa.graph.query import query_events
            topic_filter = args.get("topic")
            ev_res = query_events(self.store, topic=topic_filter)
            return json.dumps(ev_res, indent=2)

        elif name == "agtoosa_get_service_topology":
            from agtoosa.graph.query import query_topology
            svc_filter = args.get("service")
            topo_res = query_topology(self.store, service=svc_filter)
            return json.dumps(topo_res, indent=2)

        elif name == "agtoosa_get_c4_diagram":
            from agtoosa.c4.generator import C4DiagramGenerator
            generator = C4DiagramGenerator(self.store, self.workspace_root)
            lvl = args.get("level", "container")
            fmt = args.get("format", "mermaid")
            title = args.get("title")
            diagram = generator.generate(level=lvl, format_type=fmt, title=title)
            return json.dumps({
                "level": lvl,
                "format": fmt,
                "diagram": diagram
            }, indent=2)

        elif name == "agtoosa_auto_repair_pr":
            from agtoosa.repair.agent import PRAgentRepairEngine
            engine = PRAgentRepairEngine(self.store, self.workspace_root)
            dry_run = args.get("dry_run", True)
            base_ref = args.get("base_ref")
            issues = engine.diagnose(base_ref=base_ref)
            repairs = []
            for issue in issues:
                plan = engine.synthesize_repair(issue)
                if plan:
                    res = engine.apply_and_verify(plan, dry_run=dry_run)
                    repairs.append({
                        "issue": issue.to_dict(),
                        "plan": plan.to_dict(),
                        "result": res
                    })
            return json.dumps({
                "status": "clean" if not issues else ("dry_run" if dry_run else "repaired"),
                "total_issues": len(issues),
                "repairs": repairs
            }, indent=2)

        elif name == "agtoosa_run_performance_benchmark":
            from agtoosa.benchmark.harness import BenchmarkHarness
            from agtoosa.benchmark.analyzer import RegressionAnalyzer
            from agtoosa.benchmark.baseline import BenchmarkBaselineStore

            harness = BenchmarkHarness(self.store, self.workspace_root)
            baseline_store = BenchmarkBaselineStore(self.workspace_root)
            analyzer = RegressionAnalyzer(self.store, self.workspace_root, baseline_store)

            target = args.get("target")
            base_ref = args.get("base_ref")
            threshold_pct = float(args.get("threshold_pct", 10.0))
            iterations = int(args.get("iterations", 50))
            save_baseline = bool(args.get("save_baseline", False))

            targets = harness.discover_targets(base_ref=base_ref, target_path_or_symbol=target)
            results = []
            for t in targets:
                res = harness.run_benchmark(t, iterations=iterations, warmup=5)
                results.append(res)

            report = analyzer.analyze(results, threshold_pct=threshold_pct)
            if save_baseline and results:
                baseline_store.save_baseline(results)

            return json.dumps({
                "verdict": report.verdict,
                "total_benchmarked": report.total_benchmarked,
                "regressions_count": report.regressions_count,
                "threshold_pct": report.threshold_pct,
                "markdown": report.to_markdown(),
                "report": report.to_dict()
            }, indent=2)

        elif name == "agtoosa_get_socratic_audit":
            from agtoosa.review.socratic_audit import SocraticAuditEngine
            engine = SocraticAuditEngine(self.store, self.workspace_root)
            generate_blueprints = args.get("generate_blueprints", True)
            report_data = engine.run_full_audit(generate_blueprints=generate_blueprints)
            return json.dumps(report_data, indent=2)

        elif name == "agtoosa_budgeted_query":
            from agtoosa.core.topology_compiler import TopologyContextCompiler
            compiler = TopologyContextCompiler(self.store)
            query_str = args.get("query", "")
            budget = int(args.get("budget_tokens", 1500))
            strategy = args.get("strategy", "hybrid")
            pack = compiler.compile_budgeted_query(query_str, budget_tokens=budget, strategy=strategy)
            return json.dumps(pack.to_dict(), indent=2)

        elif name == "agtoosa_generate_attestation":
            from agtoosa.security.attestation import ArchitectureAttestationEngine
            engine = ArchitectureAttestationEngine(self.store, self.workspace_root)
            signing_key = args.get("signing_key")
            salt = args.get("salt")
            include_leaves = bool(args.get("include_leaves", False))
            attestation = engine.generate_attestation(signing_key=signing_key, salt=salt, include_leaves=include_leaves)
            return json.dumps(attestation, indent=2)

        elif name == "agtoosa_verify_attestation":
            from agtoosa.security.attestation import ArchitectureAttestationEngine
            attestation = args.get("attestation", {})
            signing_key = args.get("signing_key")
            valid, log = ArchitectureAttestationEngine.verify_attestation(attestation, signing_key=signing_key)
            return json.dumps({
                "valid": valid,
                "log": log,
                "merkle_root": attestation.get("merkle_root"),
                "version": attestation.get("version")
            }, indent=2)

        elif name == "agtoosa_synthesize_microservice":
            from agtoosa.federation.synthesis import MicroserviceSynthesizer
            synthesizer = MicroserviceSynthesizer(self.store, self.workspace_root)
            service_name = args.get("service_name")
            target_lang = args.get("target_lang", "python")
            fmt = args.get("format", "all")
            out_dir_str = args.get("output_dir")

            inferred_name, endpoints, schemas = synthesizer.discover_service_endpoints(service_name)
            svc_name = service_name or inferred_name

            output_dir = Path(out_dir_str) if out_dir_str else self.workspace_root / "generated" / svc_name
            files = synthesizer.synthesize_microservice_bundle(
                service_name=svc_name,
                output_dir=output_dir,
                target_lang=target_lang,
                format_type=fmt
            )
            return json.dumps({
                "status": "success",
                "service": svc_name,
                "target_lang": target_lang,
                "format": fmt,
                "endpoints_count": len(endpoints),
                "schemas_count": len(schemas),
                "files": files
            }, indent=2)

        elif name == "agtoosa_list_specs":
            import argparse
            import io
            from contextlib import redirect_stdout
            from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_spec

            target = args.get("target", "all")
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_lifecycle_spec(argparse.Namespace(target=target, json=True), self.workspace_root)
            return buf.getvalue().strip()

        elif name == "agtoosa_spectral_analysis":
            from agtoosa.graph.spectral import SpectralEngine
            nodes = self.store.get_all_nodes()
            edges = self.store.get_all_edges()
            engine = SpectralEngine(nodes, edges)
            mode = args.get("mode", "all")
            res: Dict[str, Any] = {}
            if mode in ("all", "cut"):
                res["cheeger_cut"] = engine.compute_fiedler_cut()
            if mode in ("all", "radius"):
                res["spectral_radius"] = engine.compute_spectral_radius()
            if mode in ("all", "fas"):
                res["feedback_arc_set"] = engine.compute_minimum_feedback_arc_set()
            if mode in ("all", "transitive"):
                res["transitive_reduction"] = engine.compute_transitive_reduction()
            if mode == "all":
                res["von_neumann_entropy"] = engine.compute_von_neumann_entropy()
            return json.dumps(res, indent=2)

        elif name == "agtoosa_submodular_context":
            from agtoosa.graph.query import resolve_node
            from agtoosa.core.submodular import SubmodularContextOptimizer
            target = args.get("target", "")
            budget = int(args.get("budget_tokens", 2000))
            target_node = resolve_node(self.store, target)
            if not target_node:
                return json.dumps({"error": f"Target '{target}' not found in knowledge graph"}, indent=2)

            pack_md = self.compiler.compile_context(target, hybrid=True)

            neighbors = self.store.get_neighbors(target_node["id"], direction="both")
            candidates = [n for n in neighbors if n["id"] != target_node["id"]]
            if not candidates:
                candidates = self.store.query_fts(target_node["name"], limit=25)
            seeds = [{"id": target_node["id"], "name": target_node["name"], "docstring": target_node.get("docstring", ""), "weight": 2.0}]
            optimizer = SubmodularContextOptimizer(seeds, candidates)
            opt_report = optimizer.optimize(budget_tokens=budget)
            opt_report["target"] = target_node["id"]
            opt_report["prompt_pack"] = pack_md
            return json.dumps(opt_report, indent=2)

        elif name == "agtoosa_curvature_audit":
            from agtoosa.graph.curvature import CurvatureEngine
            nodes = self.store.get_all_nodes()
            edges = self.store.get_all_edges()
            engine = CurvatureEngine(nodes, edges)
            top_k = int(args.get("top", 20))
            check_hyp = bool(args.get("hyperbolic", True))
            ric_res = engine.compute_forman_ricci_curvature()
            res = {
                "total_edges": ric_res["total_edges"],
                "average_curvature": ric_res["average_curvature"],
                "bottleneck_count": ric_res["bottleneck_count"],
                "cluster_edge_count": ric_res["cluster_edge_count"],
                "top_bottlenecks": ric_res["top_bottlenecks"][:top_k]
            }
            if check_hyp:
                res["hyperbolicity"] = engine.compute_gromov_hyperbolicity()
            return json.dumps(res, indent=2)

        elif name == "agtoosa_causal_effect":
            from agtoosa.observability.causal import CausalEngine
            from agtoosa.graph.query import resolve_node
            src_str = args.get("source", "")
            tgt_str = args.get("target", "")
            src_node = resolve_node(self.store, src_str)
            tgt_node = resolve_node(self.store, tgt_str)
            src_id = src_node["id"] if src_node else src_str
            tgt_id = tgt_node["id"] if tgt_node else tgt_str

            nodes = self.store.get_all_nodes()
            edges = self.store.get_all_edges()
            causal_eng = CausalEngine(nodes, edges)
            adj_set = causal_eng.find_minimal_adjustment_set(src_id, tgt_id)
            is_admissible, msg = causal_eng.is_backdoor_admissible(src_id, tgt_id, adj_set or set())
            obs_data = args.get("contingency_data") or []
            causal_res = causal_eng.compute_causal_effect(src_id, tgt_id, obs_data) if obs_data else None

            res = {
                "source": src_id,
                "source_name": src_node["name"] if src_node else src_id,
                "target": tgt_id,
                "target_name": tgt_node["name"] if tgt_node else tgt_id,
                "is_admissible": is_admissible,
                "minimal_adjustment_set": list(adj_set) if adj_set else [],
                "status_message": msg
            }
            if causal_res:
                res["causal_effect"] = causal_res
            return json.dumps(res, indent=2)

        return json.dumps({"error": f"Unknown tool: {name}"})


    def notify_resource_updated(self, uri: str) -> None:
        """Send a JSON-RPC notification to clients when a subscribed resource updates."""
        if uri in self.subscriptions:
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": uri}
            }
            try:
                sys.stdout.write(json.dumps(notification) + "\n")
                sys.stdout.flush()
            except OSError:
                pass

    def handle_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {"subscribe": True, "listChanged": True}
                    },
                    "serverInfo": {"name": "agtoosa-mcp", "version": __version__}
                }
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.get_tool_definitions()}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            output_text = self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": output_text}]
                }
            }
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "agtoosa://graph/stats",
                            "name": "Knowledge Graph Stats",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "agtoosa://graph/review",
                            "name": "Live Review Verdict",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }
        elif method == "resources/subscribe":
            uri = params.get("uri")
            if uri:
                self.subscriptions.add(uri)
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "resources/unsubscribe":
            uri = params.get("uri")
            if uri and uri in self.subscriptions:
                self.subscriptions.remove(uri)
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "agtoosa://graph/stats":
                text = json.dumps(self.store.get_stats().to_dict(), indent=2)
            elif uri == "agtoosa://graph/review":
                text = json.dumps(self.lifecycle.review(), indent=2)
            else:
                text = json.dumps({"error": f"Resource not found: {uri}"})
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": text}]
                }
            }

        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
        return None

    MAX_LINE_BYTES = 1024 * 1024  # 1MB limit to prevent DoS memory exhaustion

    def run_stdio(self) -> None:
        """Run standard stdio message loop with input bounds."""
        for line in sys.stdin:
            if len(line) > self.MAX_LINE_BYTES:
                continue
            line_str = line.strip()
            if not line_str:
                continue
            try:
                msg = json.loads(line_str)
                resp = self.handle_message(msg)
                if resp:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                continue
