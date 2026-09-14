"""Zero-trust semantic provider gateway, egress boundary, and prompt cache (DEV-049).

Enforces:
1. Offline-by-default posture: blocks outbound cloud egress unless explicitly enabled.
2. Zero-leak redaction: redacts API keys, credentials, and tokens before transmission.
3. Strict token and call budget ceilings: halts execution before cost overruns occur.
4. Deterministic content-addressed prompt/response caching.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from agtoosa.core.security import redact_secrets


class SemanticGatewayError(Exception):
    """Base exception for semantic provider gateway errors."""
    pass


class EgressPermissionError(SemanticGatewayError):
    """Raised when cloud egress is attempted without explicit user opt-in."""
    pass


class BudgetExceededError(SemanticGatewayError):
    """Raised when cumulative token or call budgets are exceeded."""
    pass


@dataclass
class SemanticProviderConfig:
    """Configuration for semantic model execution and egress boundaries."""
    provider_name: str = "mock"  # "mock", "local", "anthropic", "openai", "gemini"
    allow_cloud_egress: bool = False  # Zero-trust offline default (R-14 / AC-26)
    max_tokens_budget: int = 100_000
    max_requests_budget: int = 500
    cache_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.cache_dir:
            d["cache_dir"] = str(self.cache_dir)
        return d


@dataclass
class SemanticResponse:
    """Standardized response envelope from semantic provider inference."""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached: bool = False
    redacted: bool = False
    provider: str = "mock"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SemanticGateway:
    """Unified egress boundary protecting against unintended cloud transmission and cost overruns."""

    def __init__(
        self,
        config: Optional[SemanticProviderConfig] = None,
        workspace_root: Optional[Path] = None
    ):
        self.config = config or SemanticProviderConfig()
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.total_tokens_used: int = 0
        self.total_requests_made: int = 0
        self._memory_cache: Dict[str, SemanticResponse] = {}

        # Custom provider dispatch hook (e.g. for testing or external provider adapters)
        self._custom_dispatch: Optional[Callable[[str, Optional[str]], str]] = None

    def set_custom_dispatch(self, dispatcher: Optional[Callable[[str, Optional[str]], str]]) -> None:
        """Register a custom dispatch callable (e.g. for mock tests or local model)."""
        self._custom_dispatch = dispatcher

    def _get_cache_path(self, cache_key: str) -> Optional[Path]:
        if not self.config.cache_dir:
            return None
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.config.cache_dir / f"{cache_key}.json"

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1000
    ) -> SemanticResponse:
        """Send a prompt for semantic completion adhering to all security and budget controls."""
        # 1. Zero-trust offline egress check (AC-26)
        is_cloud_provider = self.config.provider_name.lower() not in {"mock", "local", "offline"}
        if is_cloud_provider and not self.config.allow_cloud_egress:
            raise EgressPermissionError(
                f"Outbound cloud egress is blocked by default for provider '{self.config.provider_name}'. "
                "Explicit opt-in is required: configure allow_cloud_egress=True."
            )

        # 2. Pre-transmission secret redaction (AC-27)
        redacted_prompt = redact_secrets(prompt)
        redacted_system = redact_secrets(system) if system else None
        was_redacted = bool((redacted_prompt != prompt) or (system is not None and redacted_system != system))

        # 3. Content-addressed deterministic caching (AC-27)
        cache_key_data = f"{self.config.provider_name}:{redacted_system or ''}:{redacted_prompt}:{max_tokens}"
        cache_key = hashlib.sha256(cache_key_data.encode("utf-8")).hexdigest()

        # Check memory cache
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            return SemanticResponse(
                content=cached.content,
                prompt_tokens=cached.prompt_tokens,
                completion_tokens=cached.completion_tokens,
                total_tokens=cached.total_tokens,
                cached=True,
                redacted=was_redacted,
                provider=self.config.provider_name,
                metadata={"cache_key": cache_key, "source": "memory_cache"}
            )

        # Check disk cache
        cache_file = self._get_cache_path(cache_key)
        if cache_file and cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                resp = SemanticResponse(
                    content=data.get("content", ""),
                    prompt_tokens=data.get("prompt_tokens", 0),
                    completion_tokens=data.get("completion_tokens", 0),
                    total_tokens=data.get("total_tokens", 0),
                    cached=True,
                    redacted=was_redacted,
                    provider=self.config.provider_name,
                    metadata={"cache_key": cache_key, "source": "disk_cache"}
                )
                self._memory_cache[cache_key] = resp
                return resp
            except Exception:
                pass

        # 4. Enforce budget ceilings (AC-27)
        if self.total_requests_made >= self.config.max_requests_budget:
            raise BudgetExceededError(
                f"Request budget limit reached: {self.total_requests_made} >= {self.config.max_requests_budget}"
            )

        # Estimate prompt tokens (approx 4 chars per token)
        est_prompt_tokens = max(1, len(redacted_prompt) // 4)
        if self.total_tokens_used + est_prompt_tokens > self.config.max_tokens_budget:
            raise BudgetExceededError(
                f"Token budget ceiling reached: {self.total_tokens_used} + {est_prompt_tokens} > {self.config.max_tokens_budget}"
            )

        # 5. Dispatch
        if self._custom_dispatch:
            content = self._custom_dispatch(redacted_prompt, redacted_system)
        elif self.config.provider_name in {"mock", "local", "offline"}:
            content = f"[MOCK_RESPONSE] Semantic completion for: {redacted_prompt[:50]}..."
        else:
            # Cloud transport would be invoked here with redacted payloads
            content = f"[CLOUD_RESPONSE] Generated by {self.config.provider_name}"

        completion_tokens = max(1, len(content) // 4)
        total_tokens = est_prompt_tokens + completion_tokens

        self.total_tokens_used += total_tokens
        self.total_requests_made += 1

        response = SemanticResponse(
            content=content,
            prompt_tokens=est_prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached=False,
            redacted=was_redacted,
            provider=self.config.provider_name,
            metadata={"cache_key": cache_key}
        )

        # Save to memory and disk cache
        self._memory_cache[cache_key] = response
        if cache_file:
            try:
                cache_file.write_text(json.dumps(response.to_dict()), encoding="utf-8")
            except Exception:
                pass

        return response
