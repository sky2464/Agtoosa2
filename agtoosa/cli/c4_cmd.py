"""CLI command handlers for C4 Architecture-as-Code & Live Diagram Sync (DEV-028)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from agtoosa.graph.store import GraphStore
from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.c4.generator import C4DiagramGenerator, C4Level, C4Format
from agtoosa.c4.sync import C4SyncManager


def _parse_level(level_str: str) -> C4Level:
    clean = str(level_str).lower().strip()
    if clean in ("1", "context"):
        return C4Level.CONTEXT
    if clean in ("2", "container"):
        return C4Level.CONTAINER
    if clean in ("3", "component"):
        return C4Level.COMPONENT
    return C4Level.CONTAINER


def cmd_c4(args: Any, workspace_root: Path) -> int:
    """Dispatcher for 'agtoosa c4' subcommands."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    action = getattr(args, "c4_action", None)

    if action == "export":
        generator = C4DiagramGenerator(store, workspace_root)
        lvl = _parse_level(getattr(args, "level", "container"))
        fmt = C4Format(getattr(args, "format", "mermaid").lower())

        diagram = generator.generate(level=lvl, format_type=fmt)

        out_path = getattr(args, "output", None)
        if out_path:
            target_file = Path(out_path)
            if not target_file.is_absolute():
                target_file = (workspace_root / target_file).resolve()
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(diagram, encoding="utf-8")
            print(f"📐 Exported C4 {lvl.value.capitalize()} Diagram ({fmt.value}):")
            print(f"   • File: {target_file}")
            return 0

        print(diagram)
        return 0

    elif action == "sync":
        sync_mgr = C4SyncManager(store, workspace_root)
        target_dir_str = getattr(args, "dir", "docs/architecture")
        target_dir = Path(target_dir_str)
        if not target_dir.is_absolute():
            target_dir = (workspace_root / target_dir).resolve()

        fmt = C4Format(getattr(args, "format", "mermaid").lower())
        check_only = getattr(args, "check", False)

        res = sync_mgr.sync_directory(target_dir, format_type=fmt, check_only=check_only)

        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
            return 0 if res["in_sync"] else 1

        rel_dir = target_dir.relative_to(workspace_root) if target_dir.is_relative_to(workspace_root) else target_dir

        if check_only:
            if res["in_sync"]:
                print(f"✅ Architecture Diagrams In Sync: {rel_dir}")
                print(f"   • Format: {fmt.value.upper()}")
                print("   • Zero architectural drifts detected.")
                return 0
            else:
                print(f"❌ Architecture Diagrams Out Of Sync ({res['total_drifts']} drifts detected):")
                print(f"   • Target Directory: {rel_dir}")
                for d in res["drifts"]:
                    reason = d.get("reason", "content_drift")
                    lvl = d.get("level", "diagram")
                    print(f"     - ⚠️  {d['file']} ({lvl}): {reason}")
                print("\n   Run 'agtoosa c4 sync' to update architecture diagrams automatically.")
                return 1
        else:
            print(f"🔄 C4 Architecture Diagrams Synchronized:")
            print(f"   • Directory: {rel_dir}")
            print(f"   • Format:    {fmt.value.upper()}")
            print(f"   • Files Updated: {sum(1 for s in res['standalone_files'] if s['written'])} standalone, {res['markdown_files_synced']} markdown docs")
            return 0

    return 0
