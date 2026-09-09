"""Base parser interface for language extractors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge


class BaseParser(ABC):
    """Abstract base class for AST and content extractors."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Return True if this parser handles the given file."""
        pass

    @abstractmethod
    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        """Extract nodes and edges from the target file."""
        pass
