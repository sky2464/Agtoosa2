"""Tests for Continuous Watcher & Git Hooks (DEV-009)."""

from pathlib import Path
import stat
import time
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine
from agtoosa.watcher.watcher import WorkspaceWatcher
from agtoosa.watcher.hooks import install_git_hooks, remove_git_hooks, get_git_hooks_status
from agtoosa.mcp.server import MCPServer


def test_watcher_poll_once(tmp_path: Path):
    ws = tmp_path / "watch_ws"
    ws.mkdir()
    f1 = ws / "module.py"
    f1.write_text("def first(): pass\n", encoding="utf-8")

    db_path = tmp_path / "watch.db"
    store = GraphStore(db_path)
    engine = ParserEngine()

    watcher = WorkspaceWatcher(ws, store, engine)

    # Initial snapshot was taken on init. Modify f1
    time.sleep(0.05)
    f1.write_text("def first(): pass\ndef second(): pass\n", encoding="utf-8")

    callbacks_received = []
    watcher.register_callback(lambda changed, stats: callbacks_received.append((changed, stats)))

    changed, stats = watcher.poll_once()
    assert "module.py" in changed
    assert stats is not None
    assert len(callbacks_received) == 1
    assert stats.total_nodes >= 3  # file + 2 funcs

    # Poll again without any modifications -> should return empty
    changed2, stats2 = watcher.poll_once()
    assert changed2 == []
    assert stats2 is None


def test_watcher_detects_new_and_deleted_files(tmp_path: Path):
    ws = tmp_path / "watch_ws2"
    ws.mkdir()
    (ws / "app.py").write_text("print(1)\n", encoding="utf-8")

    db_path = tmp_path / "watch2.db"
    store = GraphStore(db_path)
    watcher = WorkspaceWatcher(ws, store)

    # Initial state clean
    changed, _ = watcher.poll_once()
    assert changed == []

    # Add new file
    time.sleep(0.05)
    new_f = ws / "helper.py"
    new_f.write_text("def help(): pass\n", encoding="utf-8")

    changed, stats = watcher.poll_once()
    assert "helper.py" in changed
    assert stats is not None

    # Delete file
    time.sleep(0.05)
    new_f.unlink()

    changed_del, stats_del = watcher.poll_once()
    assert "helper.py" in changed_del
    assert stats_del is not None


def test_git_hooks_management(tmp_path: Path):
    ws = tmp_path / "git_repo"
    ws.mkdir()
    (ws / ".git").mkdir()

    # Install hooks
    install_res = install_git_hooks(ws)
    assert install_res.get("pre-commit") is True
    assert install_res.get("post-merge") is True
    assert install_res.get("post-checkout") is True

    # Check status
    status = get_git_hooks_status(ws)
    assert status.get("pre-commit") is True
    assert status.get("post-merge") is True
    assert status.get("post-checkout") is True

    # Check file permissions
    pre_commit = ws / ".git" / "hooks" / "pre-commit"
    assert pre_commit.is_file()
    assert bool(pre_commit.stat().st_mode & stat.S_IXUSR) is True

    # Remove hooks
    remove_res = remove_git_hooks(ws)
    assert remove_res.get("pre-commit") is True
    assert not pre_commit.exists()

    # Check status again
    status_after = get_git_hooks_status(ws)
    assert status_after.get("pre-commit") is False


def test_mcp_server_watch_and_subscriptions(tmp_path: Path):
    ws = tmp_path / "mcp_ws"
    ws.mkdir()
    (ws / "main.py").write_text("def run(): pass\n", encoding="utf-8")

    server = MCPServer(ws)

    # 1. Test agtoosa_watch_status tool
    tool_res = server.handle_tool_call("agtoosa_watch_status", {})
    assert "active" in tool_res
    assert "graph_stats" in tool_res

    # 2. Test resource subscribe and read
    sub_resp = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "resources/subscribe",
        "params": {"uri": "agtoosa://graph/stats"}
    })
    assert sub_resp is not None
    assert sub_resp["result"] == {}
    assert "agtoosa://graph/stats" in server.subscriptions

    read_resp = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/read",
        "params": {"uri": "agtoosa://graph/stats"}
    })
    assert read_resp is not None
    assert "contents" in read_resp["result"]
    assert read_resp["result"]["contents"][0]["uri"] == "agtoosa://graph/stats"

    # 3. Test unsubscribe
    unsub_resp = server.handle_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "resources/unsubscribe",
        "params": {"uri": "agtoosa://graph/stats"}
    })
    assert unsub_resp is not None
    assert "agtoosa://graph/stats" not in server.subscriptions
