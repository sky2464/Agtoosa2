"""Federation Manager: orchestrates multi-repository registration, syncing, and graph federation."""

from __future__ import annotations
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine
from agtoosa.federation.schema_parser import ContractSchemaParser
from agtoosa.federation.resolver import CrossRepoLinker


class FederationManager:
    """Manages multi-repository registrations, schema contract ingestion, and cross-repo dependency linking."""

    def __init__(self, store: GraphStore, workspace_root: Path):
        self.store = store
        self.workspace_root = workspace_root
        self.federated_cache_dir = workspace_root / ".agtoosa" / "federated"
        self.schema_parser = ContractSchemaParser()
        self.linker = CrossRepoLinker(store)

    def add_repository(
        self,
        name: str,
        uri: str,
        schema_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a new federated repository (local path or git URL)."""
        is_git = uri.startswith("http://") or uri.startswith("https://") or uri.startswith("git@")
        repo_type = "git_remote" if is_git else "local_dir"

        if is_git:
            local_path = str(self.federated_cache_dir / name)
        else:
            # Resolve relative local path against workspace_root
            cand = Path(uri)
            if not cand.is_absolute():
                cand = (self.workspace_root / uri).resolve()
            local_path = str(cand)

        self.store.add_federated_repo(
            name=name,
            uri=uri,
            local_path=local_path,
            repo_type=repo_type,
            schema_path=schema_path,
            metadata=metadata
        )

        return self.store.get_federated_repo(name) or {}

    def list_repositories(self) -> List[Dict[str, Any]]:
        """Return list of all registered federated repositories."""
        return self.store.get_federated_repos()

    def remove_repository(self, name: str) -> bool:
        """Remove a federated repository and purge its nodes from the knowledge graph."""
        return self.store.remove_federated_repo(name)

    def sync_repository(self, name: str, clean: bool = False) -> Dict[str, Any]:
        """Synchronize and index a federated repository and link cross-repo dependencies."""
        repo = self.store.get_federated_repo(name)
        if not repo:
            raise ValueError(f"Federated repository '{name}' not found.")

        if clean:
            self.store.remove_repo_nodes(name)

        local_dir = Path(repo["local_path"])
        repo_type = repo["repo_type"]
        uri = repo["uri"]

        # 1. Fetch remote git repository if needed
        if repo_type == "git_remote":
            self._fetch_or_update_git_repo(uri, local_dir)

        total_nodes = 0
        total_edges = 0

        # 2. Ingest explicit API schema contract if provided
        schema_file_str = repo.get("schema_path")
        if schema_file_str:
            schema_file = Path(schema_file_str)
            if not schema_file.is_absolute():
                schema_file = (local_dir / schema_file_str) if local_dir.exists() else (self.workspace_root / schema_file_str)

            if schema_file.exists():
                schema_nodes, schema_edges = self.schema_parser.parse_schema_file(schema_file, repo_name=name)
                if schema_nodes or schema_edges:
                    self.store.insert_batch(schema_nodes, schema_edges)
                    total_nodes += len(schema_nodes)
                    total_edges += len(schema_edges)

        # 3. If local directory exists, scan for standard schemas and source code
        if local_dir.exists() and local_dir.is_dir():
            # Auto-discover schema files in root or docs
            for candidate in ("openapi.json", "openapi.yaml", "openapi.yml", "swagger.json", "schema.proto", "schema.graphql"):
                cand_path = local_dir / candidate
                if cand_path.exists() and (not schema_file_str or cand_path.name != Path(schema_file_str).name):
                    s_nodes, s_edges = self.schema_parser.parse_schema_file(cand_path, repo_name=name)
                    if s_nodes or s_edges:
                        self.store.insert_batch(s_nodes, s_edges)
                        total_nodes += len(s_nodes)
                        total_edges += len(s_edges)

            # Index code ASTs with repo prefix to isolate namespace
            parser_engine = ParserEngine()
            sub_stats = parser_engine.index_workspace(local_dir, self.store, clean=False)
            total_nodes += sub_stats.total_nodes
            total_edges += sub_stats.total_edges

        # 4. Resolve cross-repository dependencies (consumers calling federated endpoints)
        cross_edges = self.linker.link_cross_repo_dependencies(self.workspace_root)
        if cross_edges:
            self.store.insert_batch([], cross_edges)
            total_edges += len(cross_edges)

        self.store.update_federated_repo_sync(name)

        return {
            "name": name,
            "nodes_indexed": total_nodes,
            "edges_indexed": total_edges,
            "cross_edges": len(cross_edges)
        }

    def sync_all(self, clean: bool = False) -> Dict[str, Any]:
        """Sync all registered federated repositories."""
        repos = self.list_repositories()
        results = []
        for r in repos:
            res = self.sync_repository(r["name"], clean=clean)
            results.append(res)
        return {"synced_count": len(results), "repositories": results}

    def _fetch_or_update_git_repo(self, uri: str, target_dir: Path) -> None:
        """Shallow clone or pull remote Git repository into local cache."""
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if (target_dir / ".git").exists():
            try:
                subprocess.run(["git", "pull", "--ff-only"], cwd=str(target_dir), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:
            try:
                subprocess.run(["git", "clone", "--depth", "1", uri, str(target_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
