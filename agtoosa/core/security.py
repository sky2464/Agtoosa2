"""Zero-trust security engine: secret redaction, path traversal guards, and gitignore enforcement."""

import fnmatch
from pathlib import Path
import re
from typing import List, Optional, Set

# Regex patterns for sensitive credentials & tokens
SECRET_PATTERNS = [
    # AWS Access Key ID
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED_AWS_KEY]"),
    # GitHub Personal Access Token (classic & fine-grained)
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Slack Token
    (re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"), "[REDACTED_SLACK_TOKEN]"),
    # Generic Private Key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # Generic API Key / Secret assignments
    (re.compile(r"""(?i)\b(api_key|apikey|secret_key|client_secret|auth_token|access_token|password)\b\s*[:=]\s*['"][a-zA-Z0-9_\-.~!@#$%^&*()+=]{8,}['"]"""), r"\1='[REDACTED_SECRET]'"),
    # Database Connection Strings
    (re.compile(r"""(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[^\s:]+:[^\s@]+@[^\s\/]+"""), r"\1://[USER]:[REDACTED_PASSWORD]@[HOST]")
]

# Sensitive filename patterns that must never be indexed into graph
SENSITIVE_FILENAMES = {
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    "id_ecdsa",
    "id_dsa",
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.test",
    "credentials.json",
    "service_account.json",
    "service-account.json"
}


def redact_secrets(text: Optional[str]) -> str:
    """Scan and redact known secrets, tokens, and credentials from text/docstrings."""
    if not text:
        return ""

    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def is_safe_path(candidate: Path, workspace_root: Path) -> bool:
    """Ensure candidate path resolves strictly within the canonical workspace root (prevents symlink escapes)."""
    try:
        canonical_root = workspace_root.resolve(strict=True)
        canonical_candidate = candidate.resolve(strict=False)
        return canonical_candidate.is_relative_to(canonical_root)
    except (ValueError, OSError, RuntimeError):
        return False


def is_sensitive_filename(file_path: Path) -> bool:
    """Check if filename matches known sensitive credential or key naming conventions."""
    name_lower = file_path.name.lower()
    if name_lower in SENSITIVE_FILENAMES:
        return True
    if name_lower.startswith(".env.") or name_lower.endswith((".key", ".pem", ".pfx", ".p12", ".keystore")):
        return True
    return False


def load_gitignore_patterns(workspace_root: Path) -> List[str]:
    """Load ignore patterns from repository .gitignore if present."""
    gitignore_file = workspace_root / ".gitignore"
    patterns: List[str] = []

    if not gitignore_file.is_file():
        return patterns

    try:
        content = gitignore_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    except Exception:
        pass

    return patterns


def matches_gitignore(rel_path_str: str, patterns: List[str]) -> bool:
    """Check if relative path matches any gitignore pattern."""
    # Normalize path separators
    normalized = rel_path_str.replace("\\", "/")
    path_parts = normalized.split("/")

    for pattern in patterns:
        clean_pat = pattern.rstrip("/")
        # Check direct match
        if fnmatch.fnmatch(normalized, clean_pat):
            return True
        # Check basename match
        if fnmatch.fnmatch(path_parts[-1], clean_pat):
            return True
        # Check directory prefix match
        for i in range(len(path_parts)):
            sub_path = "/".join(path_parts[:i + 1])
            if fnmatch.fnmatch(sub_path, clean_pat):
                return True

    return False
