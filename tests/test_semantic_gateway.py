"""Tests for DEV-049: Semantic Provider Gateway and Egress Boundary."""

import tempfile
from pathlib import Path
import pytest

from agtoosa.semantic.gateway import (
    SemanticGateway,
    SemanticProviderConfig,
    EgressPermissionError,
    BudgetExceededError,
)


def test_offline_by_default_blocks_cloud_egress():
    """Verify that cloud providers are blocked when allow_cloud_egress is False (AC-26)."""
    cfg = SemanticProviderConfig(provider_name="anthropic", allow_cloud_egress=False)
    gateway = SemanticGateway(cfg)

    with pytest.raises(EgressPermissionError) as excinfo:
        gateway.complete("Explain architecture invariants.")

    assert "Outbound cloud egress is blocked by default" in str(excinfo.value)


def test_cloud_egress_allowed_when_opted_in():
    """Verify that cloud providers proceed when explicit opt-in is granted."""
    cfg = SemanticProviderConfig(provider_name="openai", allow_cloud_egress=True)
    gateway = SemanticGateway(cfg)
    gateway.set_custom_dispatch(lambda prompt, sys: f"Analysis of {len(prompt)} chars")

    resp = gateway.complete("Explain invariants.")
    assert resp.cached is False
    assert "Analysis of" in resp.content
    assert resp.provider == "openai"


def test_secret_redaction_before_transmission():
    """Verify secrets are scrubbed before reaching dispatch (AC-27)."""
    cfg = SemanticProviderConfig(provider_name="mock", allow_cloud_egress=False)
    gateway = SemanticGateway(cfg)

    received_prompts = []

    def mock_dispatch(prompt, sys):
        received_prompts.append(prompt)
        return "Clean response"

    gateway.set_custom_dispatch(mock_dispatch)

    dirty_prompt = "Connect to aws with AKIA1234567890ABCDEF and github ghp_123456789012345678901234567890123456"
    resp = gateway.complete(dirty_prompt)

    assert resp.redacted is True
    assert len(received_prompts) == 1
    # Dispatch must receive redacted tokens, never raw keys!
    assert "AKIA1234567890ABCDEF" not in received_prompts[0]
    assert "[REDACTED_AWS_KEY]" in received_prompts[0]
    assert "ghp_" not in received_prompts[0]
    assert "[REDACTED_GITHUB_TOKEN]" in received_prompts[0]


def test_content_addressed_caching():
    """Verify duplicate queries hit local cache without repeating requests (AC-27)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        cfg = SemanticProviderConfig(provider_name="mock", cache_dir=cache_dir)
        gateway = SemanticGateway(cfg)

        call_count = 0

        def counting_dispatch(prompt, sys):
            nonlocal call_count
            call_count += 1
            return f"Result #{call_count}"

        gateway.set_custom_dispatch(counting_dispatch)

        # First call
        r1 = gateway.complete("What is Agtoosa?")
        assert r1.cached is False
        assert call_count == 1
        assert gateway.total_requests_made == 1

        # Second call with identical prompt
        r2 = gateway.complete("What is Agtoosa?")
        assert r2.cached is True
        assert call_count == 1  # Dispatch not called again!
        assert gateway.total_requests_made == 1  # Total requests not incremented


def test_budget_exceeded_enforcement():
    """Verify exceeding request or token limits raises BudgetExceededError (AC-27)."""
    cfg = SemanticProviderConfig(
        provider_name="mock",
        max_requests_budget=2,
        max_tokens_budget=10_000
    )
    gateway = SemanticGateway(cfg)

    # 1st request succeeds
    gateway.complete("prompt 1")
    # 2nd request succeeds
    gateway.complete("prompt 2")

    # 3rd request violates budget
    with pytest.raises(BudgetExceededError) as excinfo:
        gateway.complete("prompt 3")

    assert "Request budget limit reached" in str(excinfo.value)
