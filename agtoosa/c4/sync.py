"""Live C4 Documentation Sync Engine & CI Architecture Linter (DEV-028).

Synchronizes C4 architecture diagrams into repository documentation files (Markdown, README, docs/)
and enforces architectural diagram consistency in CI via `--check`.
"""

from __future__ import annotations
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.c4.generator import C4DiagramGenerator, C4Level, C4Format


MARKER_REGEX = re.compile(
    r'(<!--\s*agtoosa-c4-start:(\w+)\s*-->)(.*?)(<!--\s*agtoosa-c4-end:\2\s*-->)',
    re.DOTALL
)


class C4SyncManager:
    """Manages live synchronization of C4 diagrams into documentation."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()
        self.generator = C4DiagramGenerator(store, self.workspace_root)

    def sync_file(
        self,
        file_path: Path,
        format_type: C4Format | str = C4Format.MERMAID,
        check_only: bool = False
    ) -> Dict[str, Any]:
        """Sync C4 markers within a single markdown file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {file_path}")

        raw_content = file_path.read_text(encoding="utf-8")
        fmt = C4Format(format_type.lower()) if isinstance(format_type, str) else format_type

        fence_lang = "mermaid" if fmt == C4Format.MERMAID else ("plantuml" if fmt == C4Format.PLANTUML else "structurizr")

        matches_found = 0
        drifts = []

        def replacer(match: re.Match) -> str:
            nonlocal matches_found
            matches_found += 1
            start_tag = match.group(1)
            level_str = match.group(2).lower()
            current_body = match.group(3)
            end_tag = match.group(4)

            try:
                level = C4Level(level_str)
            except ValueError:
                level = C4Level.CONTAINER

            diagram = self.generator.generate(level=level, format_type=fmt)
            new_block = f"\n```{fence_lang}\n{diagram}\n```\n"

            if current_body.strip() != new_block.strip():
                drifts.append({
                    "level": level_str,
                    "file": str(file_path.relative_to(self.workspace_root) if file_path.is_relative_to(self.workspace_root) else file_path.name)
                })

            return f"{start_tag}{new_block}{end_tag}"

        new_content = MARKER_REGEX.sub(replacer, raw_content)
        has_drift = len(drifts) > 0

        if not check_only and has_drift:
            file_path.write_text(new_content, encoding="utf-8")

        return {
            "file": str(file_path),
            "markers_found": matches_found,
            "has_drift": has_drift,
            "drifts": drifts,
            "updated": has_drift and not check_only
        }

    def sync_directory(
        self,
        target_dir: Path,
        format_type: C4Format | str = C4Format.MERMAID,
        check_only: bool = False
    ) -> Dict[str, Any]:
        """Scan a directory for markdown files and standalone C4 diagrams."""
        if not target_dir.exists() and not check_only:
            target_dir.mkdir(parents=True, exist_ok=True)

        fmt = C4Format(format_type.lower()) if isinstance(format_type, str) else format_type
        ext_map = {
            C4Format.MERMAID: ".mmd",
            C4Format.PLANTUML: ".puml",
            C4Format.STRUCTURIZR: ".dsl"
        }
        target_ext = ext_map.get(fmt, ".mmd")

        # 1. Sync any existing markdown files in directory with markers
        md_results = []
        all_drifts = []

        if target_dir.exists():
            for md_file in target_dir.rglob("*.md"):
                res = self.sync_file(md_file, format_type=fmt, check_only=check_only)
                md_results.append(res)
                if res["has_drift"]:
                    all_drifts.extend(res["drifts"])

        # 2. Sync standalone diagram files for all 3 C4 levels
        standalone_files = [
            ("c4-context" + target_ext, C4Level.CONTEXT),
            ("c4-container" + target_ext, C4Level.CONTAINER),
            ("c4-component" + target_ext, C4Level.COMPONENT)
        ]

        standalone_results = []
        for fname, lvl in standalone_files:
            file_path = target_dir / fname
            expected_content = self.generator.generate(level=lvl, format_type=fmt)
            exists = file_path.exists()
            file_drift = False

            if not exists:
                file_drift = True
                all_drifts.append({"file": fname, "reason": "file_missing", "level": lvl.value})
            else:
                current_text = file_path.read_text(encoding="utf-8")
                if current_text.strip() != expected_content.strip():
                    file_drift = True
                    all_drifts.append({"file": fname, "reason": "content_drift", "level": lvl.value})

            if not check_only and file_drift:
                file_path.write_text(expected_content, encoding="utf-8")

            standalone_results.append({
                "file": str(file_path),
                "level": lvl.value,
                "drift": file_drift,
                "written": file_drift and not check_only
            })

        in_sync = len(all_drifts) == 0
        return {
            "target_dir": str(target_dir),
            "format": fmt.value,
            "in_sync": in_sync,
            "check_only": check_only,
            "total_drifts": len(all_drifts),
            "drifts": all_drifts,
            "markdown_files_synced": len(md_results),
            "standalone_files": standalone_results
        }
