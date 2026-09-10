"""Agtoosa Federation: Cross-repository knowledge graph and API contract intelligence."""

from agtoosa.federation.schema_parser import ContractSchemaParser
from agtoosa.federation.resolver import CrossRepoLinker
from agtoosa.federation.manager import FederationManager

__all__ = ["ContractSchemaParser", "CrossRepoLinker", "FederationManager"]
