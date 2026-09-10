"""Filesystem watcher for continuous incremental knowledge graph indexing."""

import hashlib
import os
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import GraphStats
from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine
from agtoosa.parser.scanner import scan_workspace


class WorkspaceWatcher:
    """Monitors workspace filesystem for file changes, debounces events, and triggers incremental graph sync."""

    def __init__(self, workspace_root: Path, store: GraphStore, engine: Optional[ParserEngine] = None):
        self.workspace_root = workspace_root.resolve()
        self.store = store
        self.engine = engine or ParserEngine()
        self._callbacks: List[Callable[[List[str], GraphStats], None]] = []
        self._stop_requested = False
        self._last_snapshot: Dict[str, float] = self._capture_mtime_snapshot()

    def register_callback(self, callback: Callable[[List[str], GraphStats], None]) -> None:
        """Register a callback to be invoked when changes are processed."""
        self._callbacks.append(callback)

    def _capture_mtime_snapshot(self) -> Dict[str, float]:
        """Capture mtime of all valid workspace source files."""
        snapshot: Dict[str, float] = {}
        files = scan_workspace(self.workspace_root)
        for fpath in files:
            try:
                rel = str(fpath.relative_to(self.workspace_root))
                snapshot[rel] = fpath.stat().st_mtime
            except (OSError, PermissionError, ValueError):
                continue
        return snapshot

    def check_changes(self) -> List[str]:
        """Detect any added, modified, or deleted files since last snapshot."""
        current_snapshot = self._capture_mtime_snapshot()
        changed: List[str] = []

        # Check modified or added
        for rel_path, mtime in current_snapshot.items():
            if rel_path not in self._last_snapshot or self._last_snapshot[rel_path] != mtime:
                changed.append(rel_path)

        # Check deleted
        for rel_path in self._last_snapshot:
            if rel_path not in current_snapshot:
                changed.append(rel_path)

        return sorted(list(set(changed)))

    def poll_once(self) -> Tuple[List[str], Optional[GraphStats]]:
        """Perform a single polling check and re-index if changes occurred."""
        changed = self.check_changes()
        if not changed:
            return [], None

        stats = self.engine.index_workspace(self.workspace_root, self.store, clean=False)
        self._last_snapshot = self._capture_mtime_snapshot()

        for cb in self._callbacks:
            try:
                cb(changed, stats)
            except Exception:
                pass

        return changed, stats

    def stop(self) -> None:
        """Signal the continuous watch loop to stop."""
        self._stop_requested = True

    def watch_forever(self, interval: float = 1.0, debounce: float = 0.5) -> None:
        """Continuously monitor workspace for changes with debouncing until stopped."""
        self._stop_requested = False
        pending_changes: Set[str] = set()
        last_change_time: Optional[float] = None

        while not self._stop_requested:
            try:
                detected = self.check_changes()
                if detected:
                    pending_changes.update(detected)
                    last_change_time = time.time()

                # Debounce window: wait until no new changes for debounce seconds
                if pending_changes and last_change_time is not None:
                    if time.time() - last_change_time >= debounce:
                        changed_list = sorted(list(pending_changes))
                        stats = self.engine.index_workspace(self.workspace_root, self.store, clean=False)
                        self._last_snapshot = self._capture_mtime_snapshot()
                        pending_changes.clear()
                        last_change_time = None

                        for cb in self._callbacks:
                            try:
                                cb(changed_list, stats)
                            except Exception:
                                pass

                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(interval)
