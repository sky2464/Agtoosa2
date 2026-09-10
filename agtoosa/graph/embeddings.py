"""Zero-dependency dense semantic embedding engine and vector search for Agtoosa2."""

from __future__ import annotations
import hashlib
import math
import re
import struct
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "of", "from", "as", "is", "are", "was", "were", "it", "this", "that"
}


class SemanticEmbeddingEngine:
    """Zero-dependency dense semantic feature vectorizer and cosine similarity search."""

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def tokenize(self, text: str) -> Dict[str, float]:
        """Tokenize text into subwords, identifiers, and character n-grams with frequency weights."""
        if not text:
            return {}

        # Split identifier camelCase and snake_case
        split_camel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
        split_clean = re.sub(r"[^a-zA-Z0-9_\-\.]", " ", split_camel)
        words = [w.lower().strip("._-") for w in split_clean.split()]

        term_counts: Dict[str, float] = {}

        for w in words:
            if not w or w in STOP_WORDS or len(w) < 2:
                continue

            # Full word token (high weight)
            full_term = f"^{w}$"
            term_counts[full_term] = term_counts.get(full_term, 0.0) + 2.0

            # Character 3-grams and 4-grams for subword similarity
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tri = w[i:i + 3]
                    term_counts[tri] = term_counts.get(tri, 0.0) + 0.8
            if len(w) >= 4:
                for i in range(len(w) - 3):
                    quad = w[i:i + 4]
                    term_counts[quad] = term_counts.get(quad, 0.0) + 1.0

        # Sublinear term frequency scaling
        weighted_terms: Dict[str, float] = {}
        for term, cnt in term_counts.items():
            weighted_terms[term] = 1.0 + math.log(cnt)

        return weighted_terms

    def embed_text(self, text: str) -> List[float]:
        """Project tokenized text into a dense fixed-dimension unit vector."""
        terms = self.tokenize(text)
        if not terms:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension

        for term, weight in terms.items():
            digest = hashlib.md5(term.encode("utf-8")).digest()
            h = int.from_bytes(digest[:8], "little")
            bucket = h % self.dimension
            sign = 1.0 if ((h >> 32) & 1) == 0 else -1.0
            vector[bucket] += sign * weight

        # L2 normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 1e-9:
            return [x / norm for x in vector]
        return [0.0] * self.dimension

    def embed_node(self, node: Dict[str, Any]) -> List[float]:
        """Construct rich semantic text for a node and generate embedding vector."""
        name = node.get("name", "")
        node_type = node.get("node_type", "")
        path = node.get("path", "")
        docstring = node.get("docstring", "") or ""

        # Emphasize name and type, include path and docstring
        corpus = f"{name} {name} {node_type} {path} {docstring}"
        return self.embed_text(corpus)

    def pack_vector(self, vector: List[float]) -> bytes:
        """Pack float array into compact binary BLOB."""
        return struct.pack(f"{len(vector)}f", *vector)

    def unpack_vector(self, blob: bytes) -> List[float]:
        """Unpack binary BLOB into float array."""
        count = len(blob) // 4
        return list(struct.unpack(f"{count}f", blob))

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two unit-normalized vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return max(0.0, min(1.0, dot))

    def build_embeddings(self, store: GraphStore, clean: bool = False) -> Dict[str, Any]:
        """Index all nodes in GraphStore into node_embeddings table."""
        if clean:
            store.clear_embeddings()

        nodes = store.get_all_nodes()
        embeddings: Dict[str, bytes] = {}

        for n in nodes:
            vec = self.embed_node(n)
            embeddings[n["id"]] = self.pack_vector(vec)

        if embeddings:
            store.save_embeddings(embeddings, self.dimension)

        return {
            "indexed_count": len(embeddings),
            "dimension": self.dimension
        }

    def search(self, store: GraphStore, query: str, top_k: int = 10, min_score: float = 0.02) -> List[Dict[str, Any]]:
        """Dense semantic vector similarity search against all stored node embeddings."""
        all_embeddings = store.get_all_embeddings()
        if not all_embeddings:
            # Auto-build on first search if store has nodes but no embeddings
            self.build_embeddings(store)
            all_embeddings = store.get_all_embeddings()

        if not all_embeddings:
            return []

        query_vec = self.embed_text(query)

        scored: List[Tuple[str, float]] = []
        for node_id, blob in all_embeddings.items():
            node_vec = self.unpack_vector(blob)
            score = self.cosine_similarity(query_vec, node_vec)
            if score >= min_score:
                scored.append((node_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored[:top_k]

        results: List[Dict[str, Any]] = []
        for rank, (node_id, score) in enumerate(top_matches, start=1):
            node = store.get_node(node_id)
            if node:
                results.append({
                    "node": node,
                    "score": round(score, 4),
                    "rank": rank
                })

        return results
