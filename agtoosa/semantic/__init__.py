"""Unified Semantic Provider Gateway and Zero-Trust Egress Boundary (DEV-049)."""

from agtoosa.semantic.gateway import (
    SemanticGateway,
    SemanticProviderConfig,
    SemanticResponse,
    SemanticGatewayError,
    EgressPermissionError,
    BudgetExceededError,
)

__all__ = [
    "SemanticGateway",
    "SemanticProviderConfig",
    "SemanticResponse",
    "SemanticGatewayError",
    "EgressPermissionError",
    "BudgetExceededError",
]
