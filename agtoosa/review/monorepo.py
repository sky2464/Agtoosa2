"""Monorepo Package Boundary Enforcement Engine (DEV-016 / Stage 16).

Discovers workspace packages (npm, pnpm, Cargo, Python, and convention-based monorepos),
extracts package manifests and declared dependencies, and validates inter-package
architectural boundaries against the knowledge graph:
- Encapsulation leaks (importing internal/private files instead of public exports)
- Undeclared workspace dependencies (importing sibling package without manifest declaration)
- Circular package dependencies (directed package graph cycles)
- Scope / tag policy violations (e.g. domain core importing presentation apps)
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore


@dataclass
class WorkspacePackage:
    name: str
    path: str  # relative to workspace_root, e.g. "packages/ui"
    abs_path: Path
    manifest_path: Optional[Path] = None
    manifest_type: str = "generic"  # "npm", "cargo", "python", "generic"
    scope: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    public_exports: List[str] = field(default_factory=list)
    declared_dependencies: Set[str] = field(default_factory=set)
    allow_internal_access: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "manifest_type": self.manifest_type,
            "scope": self.scope,
            "tags": self.tags,
            "public_exports": self.public_exports,
            "declared_dependencies": sorted(list(self.declared_dependencies)),
            "allow_internal_access": self.allow_internal_access,
        }


@dataclass
class BoundaryViolation:
    rule: str  # "ENCAPSULATION_LEAK", "UNDECLARED_DEPENDENCY", "CIRCULAR_PACKAGE_DEPENDENCY", "SCOPE_VIOLATION"
    severity: str  # "ERROR", "WARNING"
    source_package: str
    target_package: str
    source_file: str
    target_file: str
    message: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MonorepoReport:
    is_monorepo: bool
    packages: List[Dict[str, Any]] = field(default_factory=list)
    package_dependencies: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[BoundaryViolation] = field(default_factory=list)
    cycles: List[List[str]] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_monorepo": self.is_monorepo,
            "packages_count": len(self.packages),
            "packages": self.packages,
            "package_dependencies": self.package_dependencies,
            "violations_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "cycles": self.cycles,
            "passed": self.passed,
        }


class MonorepoBoundaryEngine:
    """Enforces monorepo package isolation and public export encapsulation."""

    DEFAULT_CONVENTIONS = ["packages/*", "apps/*", "libs/*", "modules/*", "crates/*"]

    def __init__(self, workspace_root: Path, store: Optional[GraphStore] = None):
        self.workspace_root = workspace_root.resolve()
        self.store = store
        self.packages: Dict[str, WorkspacePackage] = {}
        self.custom_rules: List[Dict[str, Any]] = []

    def discover_packages(self) -> Dict[str, WorkspacePackage]:
        """Discover all workspace packages in the monorepo."""
        self.packages.clear()
        self._load_custom_config()

        patterns: List[str] = []

        # 1. pnpm-workspace.yaml
        pnpm_ws = self.workspace_root / "pnpm-workspace.yaml"
        if pnpm_ws.exists():
            patterns.extend(self._parse_pnpm_workspace(pnpm_ws))

        # 2. Root package.json workspaces
        root_pkg = self.workspace_root / "package.json"
        if root_pkg.exists():
            patterns.extend(self._parse_npm_workspaces(root_pkg))

        # 3. Cargo.toml workspace
        root_cargo = self.workspace_root / "Cargo.toml"
        if root_cargo.exists():
            patterns.extend(self._parse_cargo_workspace(root_cargo))

        # 4. Fallback: check default convention folders if no patterns found
        if not patterns:
            for conv in self.DEFAULT_CONVENTIONS:
                base = conv.split("/*")[0]
                if (self.workspace_root / base).is_dir():
                    patterns.append(conv)

        # Expand glob patterns
        package_dirs: Set[Path] = set()
        for pat in patterns:
            for matched in self.workspace_root.glob(pat):
                if matched.is_dir() and matched != self.workspace_root:
                    package_dirs.add(matched)

        # Inspect each discovered directory
        for pdir in sorted(package_dirs):
            pkg = self._inspect_package_dir(pdir)
            if pkg:
                self.packages[pkg.name] = pkg

        return self.packages

    def _load_custom_config(self) -> None:
        """Load optional .agtoosa/boundaries.json or .agtoosa/monorepo.json."""
        for cfg_rel in [".agtoosa/boundaries.json", ".agtoosa/monorepo.json"]:
            cfg_path = self.workspace_root / cfg_rel
            if cfg_path.exists():
                try:
                    data = json.loads(cfg_path.read_text(encoding="utf-8"))
                    self.custom_rules = data.get("rules", [])
                    # Pre-load custom package definitions if any
                    for pkg_def in data.get("packages", []):
                        pname = pkg_def.get("name")
                        rel_path = pkg_def.get("path")
                        if pname and rel_path:
                            abs_p = (self.workspace_root / rel_path).resolve()
                            if abs_p.is_dir():
                                pkg = WorkspacePackage(
                                    name=pname,
                                    path=rel_path,
                                    abs_path=abs_p,
                                    scope=pkg_def.get("scope"),
                                    tags=pkg_def.get("tags", []),
                                    public_exports=pkg_def.get("public_exports", []),
                                    allow_internal_access=pkg_def.get("allow_internal_access", False),
                                )
                                self.packages[pname] = pkg
                except Exception:
                    pass

    def _parse_pnpm_workspace(self, path: Path) -> List[str]:
        patterns = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            in_packages = False
            for line in lines:
                s = line.strip()
                if s.startswith("packages:"):
                    in_packages = True
                    continue
                if in_packages:
                    if s.startswith("-"):
                        item = s.lstrip("-").strip().strip("'\"")
                        patterns.append(item)
                    elif s and not s.startswith("#"):
                        break
        except Exception:
            pass
        return patterns

    def _parse_npm_workspaces(self, path: Path) -> List[str]:
        patterns = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ws = data.get("workspaces")
            if isinstance(ws, list):
                patterns.extend(ws)
            elif isinstance(ws, dict):
                packages = ws.get("packages")
                if isinstance(packages, list):
                    patterns.extend(packages)
        except Exception:
            pass
        return patterns

    def _parse_cargo_workspace(self, path: Path) -> List[str]:
        patterns = []
        try:
            content = path.read_text(encoding="utf-8")
            if "[workspace]" in content:
                match = re.search(r'members\s*=\s*\[(.*?)\]', content, re.DOTALL)
                if match:
                    items = re.findall(r'["\'](.*?)["\']', match.group(1))
                    patterns.extend(items)
        except Exception:
            pass
        return patterns

    def _inspect_package_dir(self, pdir: Path) -> Optional[WorkspacePackage]:
        """Inspect a candidate directory and extract manifest/package metadata."""
        rel_path = str(pdir.relative_to(self.workspace_root)).replace("\\", "/")
        name = pdir.name
        manifest_type = "generic"
        manifest_path = None
        declared_deps: Set[str] = set()
        public_exports: List[str] = []

        # 1. Check package.json
        pkg_json = pdir / "package.json"
        if pkg_json.exists():
            manifest_type = "npm"
            manifest_path = pkg_json
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                name = data.get("name", name)
                # Dependencies
                for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
                    for dep in data.get(dep_key, {}).keys():
                        declared_deps.add(dep)
                # Exports / entrypoints
                if "main" in data:
                    public_exports.append(data["main"])
                if "exports" in data:
                    exports = data["exports"]
                    if isinstance(exports, str):
                        public_exports.append(exports)
                    elif isinstance(exports, dict):
                        for k, v in exports.items():
                            if isinstance(v, str):
                                public_exports.append(v)
                            elif isinstance(v, dict):
                                for sub_k, sub_v in v.items():
                                    if isinstance(sub_v, str):
                                        public_exports.append(sub_v)
            except Exception:
                pass

        # 2. Check Cargo.toml
        cargo_toml = pdir / "Cargo.toml"
        if not manifest_path and cargo_toml.exists():
            manifest_type = "cargo"
            manifest_path = cargo_toml
            try:
                content = cargo_toml.read_text(encoding="utf-8")
                pkg_match = re.search(r'name\s*=\s*["\'](.*?)["\']', content)
                if pkg_match:
                    name = pkg_match.group(1)
                # Dependencies
                deps_matches = re.findall(r'\[dependencies\.(.*?)\]', content)
                declared_deps.update(deps_matches)
                # Standard cargo lib
                if (pdir / "src/lib.rs").exists():
                    public_exports.append("src/lib.rs")
            except Exception:
                pass

        # 3. Check pyproject.toml / setup.py
        pyproject = pdir / "pyproject.toml"
        if not manifest_path and pyproject.exists():
            manifest_type = "python"
            manifest_path = pyproject
            try:
                content = pyproject.read_text(encoding="utf-8")
                name_match = re.search(r'name\s*=\s*["\'](.*?)["\']', content)
                if name_match:
                    name = name_match.group(1)
                # dependencies
                deps = re.findall(r'["\']([a-zA-Z0-9_\-]+)[><=~^]', content)
                declared_deps.update(deps)
            except Exception:
                pass

        # Default public exports if none declared
        if not public_exports:
            for candidate in ("src/index.ts", "src/index.js", "index.ts", "index.js", "__init__.py", "src/lib.rs"):
                if (pdir / candidate).exists():
                    public_exports.append(candidate)

        # Check if already registered from custom config
        if name in self.packages:
            existing = self.packages[name]
            existing.manifest_path = manifest_path
            existing.manifest_type = manifest_type
            if not existing.public_exports and public_exports:
                existing.public_exports = public_exports
            existing.declared_dependencies.update(declared_deps)
            return existing

        # Infer scope from path
        scope = None
        if "app" in rel_path.lower():
            scope = "app"
        elif "lib" in rel_path.lower():
            scope = "lib"
        elif "tool" in rel_path.lower():
            scope = "tool"
        elif "core" in rel_path.lower():
            scope = "core"

        return WorkspacePackage(
            name=name,
            path=rel_path,
            abs_path=pdir,
            manifest_path=manifest_path,
            manifest_type=manifest_type,
            scope=scope,
            public_exports=public_exports,
            declared_dependencies=declared_deps,
        )

    def check_boundaries(self, strict: bool = False) -> MonorepoReport:
        """Analyze package boundaries across the knowledge graph and codebase."""
        self.discover_packages()

        if len(self.packages) < 2:
            return MonorepoReport(
                is_monorepo=False,
                packages=[p.to_dict() for p in self.packages.values()],
                passed=True,
            )

        violations: List[BoundaryViolation] = []
        package_deps_map: Dict[str, Set[str]] = {p: set() for p in self.packages}
        inter_package_calls: List[Dict[str, Any]] = []

        # Analyze edges from GraphStore if available, otherwise parse AST/imports
        cross_edges = self._extract_cross_package_edges()

        for edge in cross_edges:
            src_pkg_name = edge["source_package"]
            tgt_pkg_name = edge["target_package"]
            src_file = edge["source_file"]
            tgt_file = edge["target_file"]

            package_deps_map[src_pkg_name].add(tgt_pkg_name)
            inter_package_calls.append(edge)

            src_pkg = self.packages[src_pkg_name]
            tgt_pkg = self.packages[tgt_pkg_name]

            # Rule 1: Encapsulation Leak
            # If target file is an internal module (matches internal/, private/, _*, or not in public exports)
            is_internal = self._is_internal_module(tgt_pkg, tgt_file)
            if is_internal and not tgt_pkg.allow_internal_access:
                violations.append(
                    BoundaryViolation(
                        rule="ENCAPSULATION_LEAK",
                        severity="ERROR",
                        source_package=src_pkg_name,
                        target_package=tgt_pkg_name,
                        source_file=src_file,
                        target_file=tgt_file,
                        message=(
                            f"Package '{src_pkg_name}' bypasses public API of '{tgt_pkg_name}' "
                            f"to import internal module '{tgt_file}'."
                        ),
                        remediation=(
                            f"Export the required symbol via '{tgt_pkg_name}' public entrypoint "
                            f"({', '.join(tgt_pkg.public_exports) or 'index.ts / __init__.py'}) "
                            f"instead of directly importing internal files."
                        ),
                    )
                )

            # Rule 2: Undeclared Workspace Dependency
            if (
                tgt_pkg_name not in src_pkg.declared_dependencies
                and tgt_pkg.name not in src_pkg.declared_dependencies
                and tgt_pkg.path not in src_pkg.declared_dependencies
            ):
                violations.append(
                    BoundaryViolation(
                        rule="UNDECLARED_DEPENDENCY",
                        severity="ERROR",
                        source_package=src_pkg_name,
                        target_package=tgt_pkg_name,
                        source_file=src_file,
                        target_file=tgt_file,
                        message=(
                            f"Package '{src_pkg_name}' imports from sibling package '{tgt_pkg_name}', "
                            f"but '{tgt_pkg_name}' is not declared in '{src_pkg.manifest_path or src_pkg.path}'."
                        ),
                        remediation=(
                            f"Add \"{tgt_pkg_name}\": \"workspace:*\" to '{src_pkg.path}' manifest dependencies."
                        ),
                    )
                )

            # Rule 3: Custom Scope / Tag Policy Violations
            for rule in self.custom_rules:
                if self._violates_custom_rule(rule, src_pkg, tgt_pkg):
                    violations.append(
                        BoundaryViolation(
                            rule="SCOPE_VIOLATION",
                            severity=rule.get("severity", "ERROR"),
                            source_package=src_pkg_name,
                            target_package=tgt_pkg_name,
                            source_file=src_file,
                            target_file=tgt_file,
                            message=rule.get(
                                "message",
                                f"Package '{src_pkg_name}' (scope: {src_pkg.scope}) is not permitted to import '{tgt_pkg_name}' (scope: {tgt_pkg.scope}).",
                            ),
                            remediation="Refactor architecture to decouple dependencies according to project policy.",
                        )
                    )

        # Rule 4: Circular Package Dependencies
        cycles = self._find_package_cycles(package_deps_map)
        for cycle in cycles:
            cycle_str = " ➔ ".join(cycle)
            violations.append(
                BoundaryViolation(
                    rule="CIRCULAR_PACKAGE_DEPENDENCY",
                    severity="ERROR",
                    source_package=cycle[0],
                    target_package=cycle[-1],
                    source_file=self.packages[cycle[0]].path,
                    target_file=self.packages[cycle[1]].path if len(cycle) > 1 else "",
                    message=f"Circular dependency detected between workspace packages: {cycle_str}",
                    remediation="Extract shared types/interfaces to a common package or introduce dependency inversion.",
                )
            )

        # Deduplicate violations by rule + source_package + target_package + target_file
        unique_violations: List[BoundaryViolation] = []
        seen_keys: Set[Tuple[str, str, str, str]] = set()
        for v in violations:
            key = (v.rule, v.source_package, v.target_package, v.target_file)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_violations.append(v)

        passed = True
        if strict:
            passed = len(unique_violations) == 0
        else:
            errors = [v for v in unique_violations if v.severity == "ERROR"]
            passed = len(errors) == 0

        # Build package dependencies list
        package_dep_list = []
        for src, tgts in package_deps_map.items():
            for tgt in sorted(tgts):
                package_dep_list.append({"from": src, "to": tgt})

        return MonorepoReport(
            is_monorepo=True,
            packages=[p.to_dict() for p in self.packages.values()],
            package_dependencies=package_dep_list,
            violations=unique_violations,
            cycles=cycles,
            passed=passed,
        )

    def _is_internal_module(self, pkg: WorkspacePackage, rel_file_path: str) -> bool:
        """Check if a file inside a package is considered internal."""
        norm = rel_file_path.replace("\\", "/").lower()
        pkg_norm = pkg.path.replace("\\", "/").lower()

        # Extract path relative to package root
        if norm.startswith(pkg_norm + "/"):
            sub_path = norm[len(pkg_norm) + 1:]
        else:
            sub_path = norm

        # Explicit internal directory patterns
        internal_indicators = [
            "/internal/", "internal/",
            "/private/", "private/",
            "/_private/", "_private/",
            "/impl/", "impl/",
        ]
        if any(ind in sub_path for ind in internal_indicators):
            return True

        # If package declares explicit public exports, any file not matching public exports is internal
        if pkg.public_exports:
            norm_exports = [
                exp.replace("\\", "/").lower().lstrip("./") for exp in pkg.public_exports
            ]
            # Match sub_path or sub_path without extension
            sub_base = sub_path.rsplit(".", 1)[0]
            for exp in norm_exports:
                exp_base = exp.rsplit(".", 1)[0]
                if sub_path == exp or sub_base == exp_base or sub_path.endswith(exp):
                    return False
            # Not in declared public exports
            return True

        return False

    def _violates_custom_rule(
        self, rule: Dict[str, Any], src_pkg: WorkspacePackage, tgt_pkg: WorkspacePackage
    ) -> bool:
        """Evaluate custom boundaries rules from .agtoosa/boundaries.json."""
        src_scope = rule.get("source_scope")
        disallow_scopes = rule.get("disallow_scopes", rule.get("disallow", []))
        if src_scope and src_pkg.scope == src_scope:
            if disallow_scopes and tgt_pkg.scope and tgt_pkg.scope in disallow_scopes:
                return True

        src_name = rule.get("source_package")
        disallow_pkgs = rule.get("disallow_packages", [])
        if (src_name == "*" or src_name == src_pkg.name) and tgt_pkg.name in disallow_pkgs:
            return True

        return False

    def _extract_cross_package_edges(self) -> List[Dict[str, Any]]:
        """Extract all inter-package import/call edges."""
        cross_edges: List[Dict[str, Any]] = []

        # 1. From GraphStore if populated
        if self.store:
            edges = self.store.get_all_edges()
            for edge in edges:
                if edge.get("edge_type") not in ("imports", "calls", "depends_on"):
                    continue

                src_id = edge["source_id"]
                tgt_id = edge["target_id"]

                src_node = self.store.get_node(src_id)
                tgt_node = self.store.get_node(tgt_id)

                if not src_node or not tgt_node:
                    continue

                src_file = src_node.get("path", "")
                tgt_file = tgt_node.get("path", "")

                src_pkg = self._find_package_for_file(src_file)
                tgt_pkg = self._find_package_for_file(tgt_file)

                if src_pkg and tgt_pkg and src_pkg != tgt_pkg:
                    cross_edges.append({
                        "source_package": src_pkg.name,
                        "target_package": tgt_pkg.name,
                        "source_file": src_file,
                        "target_file": tgt_file,
                    })

        # 2. Source code scanning fallback/supplement
        if not cross_edges:
            cross_edges = self._scan_source_imports()

        return cross_edges

    def _find_package_for_file(self, rel_path: str) -> Optional[WorkspacePackage]:
        """Map a relative file path to its owning workspace package."""
        norm = rel_path.replace("\\", "/").lstrip("./")
        # Match longest matching package path
        best_match: Optional[WorkspacePackage] = None
        best_len = 0
        for pkg in self.packages.values():
            pkg_path = pkg.path.replace("\\", "/").lstrip("./")
            if norm == pkg_path or norm.startswith(pkg_path + "/"):
                if len(pkg_path) > best_len:
                    best_match = pkg
                    best_len = len(pkg_path)
        return best_match

    def _scan_source_imports(self) -> List[Dict[str, Any]]:
        """Scan source files directly for inter-package import statements."""
        cross_edges: List[Dict[str, Any]] = []
        extensions = (".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go")

        for pkg in self.packages.values():
            for fpath in pkg.abs_path.rglob("*"):
                if not fpath.is_file() or fpath.suffix not in extensions:
                    continue
                # Skip node_modules, target, venv
                if any(x in fpath.parts for x in ("node_modules", "target", ".venv", "__pycache__", "dist", "build")):
                    continue

                rel_file = str(fpath.relative_to(self.workspace_root)).replace("\\", "/")
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    imports = self._extract_imports_from_text(content, fpath.suffix)
                    for imp in imports:
                        resolved_tgt, tgt_file = self._resolve_import_target(pkg, imp, fpath)
                        if resolved_tgt and resolved_tgt.name != pkg.name:
                            cross_edges.append({
                                "source_package": pkg.name,
                                "target_package": resolved_tgt.name,
                                "source_file": rel_file,
                                "target_file": tgt_file,
                            })
                except Exception:
                    pass

        return cross_edges

    def _extract_imports_from_text(self, text: str, ext: str) -> List[str]:
        """Extract import module strings using regex."""
        imports = []
        if ext in (".ts", ".tsx", ".js", ".jsx"):
            # import ... from '...' or require('...')
            matches = re.findall(r'''(?:import\s+.*?from\s+|require\s*\()\s*['"]([^'"]+)['"]''', text)
            imports.extend(matches)
        elif ext == ".py":
            # from x import y or import x
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("from "):
                    m = re.match(r'from\s+([a-zA-Z0-9_\.]+)', line)
                    if m:
                        imports.append(m.group(1))
                elif line.startswith("import "):
                    m = re.match(r'import\s+([a-zA-Z0-9_\.]+)', line)
                    if m:
                        imports.append(m.group(1))
        elif ext == ".rs":
            matches = re.findall(r'use\s+([a-zA-Z0-9_]+)::', text)
            imports.extend(matches)
        return imports

    def _resolve_import_target(
        self, src_pkg: WorkspacePackage, import_path: str, src_file: Path
    ) -> Tuple[Optional[WorkspacePackage], str]:
        """Resolve an import string to target workspace package and target file."""
        # 1. Direct package name match
        for tgt_pkg in self.packages.values():
            if import_path == tgt_pkg.name or import_path.startswith(tgt_pkg.name + "/"):
                sub_path = import_path[len(tgt_pkg.name):].lstrip("/")
                tgt_file = f"{tgt_pkg.path}/{sub_path}" if sub_path else f"{tgt_pkg.path}/index"
                return tgt_pkg, tgt_file

        # 2. Relative import traversing outside src_pkg root
        if import_path.startswith("."):
            try:
                resolved_path = (src_file.parent / import_path).resolve()
                if self.workspace_root in resolved_path.parents or resolved_path == self.workspace_root:
                    rel_to_ws = str(resolved_path.relative_to(self.workspace_root)).replace("\\", "/")
                    tgt_pkg = self._find_package_for_file(rel_to_ws)
                    if tgt_pkg:
                        return tgt_pkg, rel_to_ws
            except Exception:
                pass

        return None, ""

    def _find_package_cycles(self, deps_map: Dict[str, Set[str]]) -> List[List[str]]:
        """Find all directed cycles in the workspace package dependency graph."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        current_path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            current_path.append(node)

            for neighbor in sorted(deps_map.get(node, set())):
                if neighbor not in deps_map:
                    continue
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    idx = current_path.index(neighbor)
                    cycle = current_path[idx:] + [neighbor]
                    cycles.append(cycle)

            current_path.pop()
            rec_stack.remove(node)

        for pkg in sorted(deps_map.keys()):
            if pkg not in visited:
                dfs(pkg)

        return cycles
