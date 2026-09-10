"""Tests for Zero-Trust Security Hardening (DEV-007)."""

import os
from pathlib import Path
import pytest

from agtoosa.core.security import (
    is_safe_path,
    is_sensitive_filename,
    redact_secrets,
    load_gitignore_patterns,
    matches_gitignore,
)
from agtoosa.parser.scanner import scan_workspace
from agtoosa.graph.store import GraphStore
from agtoosa.graph.visualizer import VisualizerEngine
from agtoosa.core.model import Node, NodeType


def test_is_safe_path(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    inside_file = root / "src" / "app.py"
    inside_file.parent.mkdir()
    inside_file.touch()

    # Normal inside path
    assert is_safe_path(inside_file, root) is True

    # Path outside workspace
    outside_file = tmp_path / "outside.txt"
    outside_file.touch()
    assert is_safe_path(outside_file, root) is False

    # Path traversal with ..
    traversal_path = root / ".." / "outside.txt"
    assert is_safe_path(traversal_path, root) is False

    # Symlink escaping root
    symlink_outside = root / "escape_link"
    try:
        symlink_outside.symlink_to(outside_file)
        assert is_safe_path(symlink_outside, root) is False
    except OSError:
        pass


def test_is_sensitive_filename():
    assert is_sensitive_filename(Path(".env")) is True
    assert is_sensitive_filename(Path(".env.production")) is True
    assert is_sensitive_filename(Path("id_rsa")) is True
    assert is_sensitive_filename(Path("server.key")) is True
    assert is_sensitive_filename(Path("cert.pem")) is True
    assert is_sensitive_filename(Path("credentials.json")) is True
    assert is_sensitive_filename(Path("service_account.json")) is True
    assert is_sensitive_filename(Path("deploy.keystore")) is True

    # Benign filenames
    assert is_sensitive_filename(Path("main.py")) is False
    assert is_sensitive_filename(Path("README.md")) is False
    assert is_sensitive_filename(Path("config.py")) is False


def test_redact_secrets():
    # AWS Key pattern
    text_aws = "Deploy with AKIAIOSFODNN7EXAMPLE key."
    redacted = redact_secrets(text_aws)
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted

    # Slack token
    text_slack = "token = 'xoxb-123456789012-abcdefghijklmnopqrstuvwx'"
    redacted_slack = redact_secrets(text_slack)
    assert "[REDACTED_SLACK_TOKEN]" in redacted_slack
    assert "xoxb-" not in redacted_slack

    # Private key block
    text_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    redacted_key = redact_secrets(text_key)
    assert "[REDACTED_PRIVATE_KEY]" in redacted_key
    assert "MIIEowIBAAKCAQEA" not in redacted_key

    # Regular docstring untouched
    normal = "This function calculates the fibonacci series for n > 0."
    assert redact_secrets(normal) == normal


def test_gitignore_matching(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    gi = root / ".gitignore"
    gi.write_text("*.log\nbuild/\nsecret_dir/*\n", encoding="utf-8")

    patterns = load_gitignore_patterns(root)
    assert len(patterns) >= 3

    assert matches_gitignore("error.log", patterns) is True
    assert matches_gitignore("sub/test.log", patterns) is True
    assert matches_gitignore("build/output.js", patterns) is True
    assert matches_gitignore("src/main.py", patterns) is False


def test_scanner_omits_sensitive_files(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "main.py").write_text("print('hello')", encoding="utf-8")
    (ws / ".env").write_text("API_KEY=secret", encoding="utf-8")
    (ws / "id_rsa").write_text("privatekey", encoding="utf-8")
    (ws / "app.key").write_text("keydata", encoding="utf-8")

    scanned = scan_workspace(ws)
    scanned_names = [f.name for f in scanned]

    assert "main.py" in scanned_names
    assert ".env" not in scanned_names
    assert "id_rsa" not in scanned_names
    assert "app.key" not in scanned_names


def test_visualizer_csp_and_anti_xss(tmp_path: Path):
    db_path = tmp_path / "test.db"
    store = GraphStore(db_path)

    # Insert node with potentially malicious XSS payload
    xss_node = Node(
        id="file:evil.py",
        name="<script>alert('xss')</script>",
        node_type=NodeType.FILE,
        path="evil.py",
        docstring="<img src=x onerror=alert(1)>"
    )
    store.insert_batch([xss_node], [])

    visualizer = VisualizerEngine(store)
    html_content = visualizer.generate_html()

    # Verify CSP meta tag exists
    assert "Content-Security-Policy" in html_content
    assert "default-src 'self' 'unsafe-inline'" in html_content

    # Verify escapeHtml helper is injected
    assert "function escapeHtml" in html_content

    # Verify unescaped raw <script>alert is NOT directly rendered as unescaped DOM markup
    assert "<script>alert('xss')</script>" not in html_content.replace(xss_node.name, "")
