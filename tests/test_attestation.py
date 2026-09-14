"""Tests for DEV-038: Zero-Knowledge Architecture Cryptographic Attestation."""

import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.security.attestation import ArchitectureAttestationEngine
from agtoosa.mcp.server import MCPServer
from agtoosa.cli.main import main


class TestArchitectureAttestation(unittest.TestCase):
    """Test suite for zero-knowledge architectural cryptographic attestation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.temp_dir.name)
        self.db_path = self.workspace_root / "test_graph.db"
        self.store = GraphStore(self.db_path)
        self.engine = ArchitectureAttestationEngine(self.store, self.workspace_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_blind_id_properties(self):
        """Salted commitments must be deterministic per salt and unique across salts."""
        raw_id = "function:agtoosa/core/model.py:Node"
        salt1 = "abcd1234efgh5678"
        salt2 = "9999888877776666"

        blind1_a = ArchitectureAttestationEngine.blind_id(raw_id, salt1)
        blind1_b = ArchitectureAttestationEngine.blind_id(raw_id, salt1)
        blind2 = ArchitectureAttestationEngine.blind_id(raw_id, salt2)

        self.assertEqual(blind1_a, blind1_b)
        self.assertNotEqual(blind1_a, blind2)
        self.assertEqual(len(blind1_a), 64)
        self.assertNotIn(raw_id, blind1_a)

    def test_merkle_root_construction(self):
        """Merkle root must be deterministic regardless of leaf input order."""
        leaves = [
            "a" * 64,
            "b" * 64,
            "c" * 64,
            "d" * 64
        ]
        root1 = ArchitectureAttestationEngine.compute_merkle_root(leaves)
        root2 = ArchitectureAttestationEngine.compute_merkle_root(list(reversed(leaves)))
        self.assertEqual(root1, root2)
        self.assertEqual(len(root1), 64)

        empty_root = ArchitectureAttestationEngine.compute_merkle_root([])
        self.assertEqual(len(empty_root), 64)

    def test_generate_and_verify_compliant_attestation(self):
        """Compliant graph with Tier 1 -> Tier 2 -> Tier 3 must generate verified attestation."""
        nodes = [
            Node(id="fn:cli", name="cli_entry", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py"),
            Node(id="fn:parser", name="parse_file", node_type=NodeType.FUNCTION, path="agtoosa/parser/py_parser.py"),
            Node(id="fn:core", name="Node", node_type=NodeType.CLASS, path="agtoosa/core/model.py"),
        ]
        edges = [
            Edge(source_id="fn:cli", target_id="fn:parser", edge_type=EdgeType.CALLS),
            Edge(source_id="fn:parser", target_id="fn:core", edge_type=EdgeType.IMPORTS),
        ]
        self.store.insert_batch(nodes, edges)

        secret_key = "super-secret-signing-key-123"
        attestation = self.engine.generate_attestation(signing_key=secret_key, include_leaves=True)

        self.assertEqual(attestation["version"], "1.0")
        self.assertEqual(attestation["node_count"], 3)
        self.assertEqual(attestation["edge_count"], 2)
        self.assertEqual(attestation["violations_count"], 0)
        self.assertEqual(attestation["cycles_count"], 0)
        self.assertEqual(attestation["compliant_leaf_count"], 2)
        self.assertIsNotNone(attestation["signature"])

        # Ensure no confidential plain text is leaked
        attestation_json = json.dumps(attestation)
        self.assertNotIn("agtoosa/cli/main.py", attestation_json)
        self.assertNotIn("agtoosa/core/model.py", attestation_json)
        self.assertNotIn("cli_entry", attestation_json)

        # Verify
        valid, log = ArchitectureAttestationEngine.verify_attestation(attestation, signing_key=secret_key)
        self.assertTrue(valid)
        self.assertTrue(any("Verified Successfully" in line for line in log))

    def test_verify_fails_on_tampered_signature(self):
        """Tampering with signed attestation must be rejected."""
        self.store.insert_batch(
            [Node(id="fn:1", name="f1", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py")],
            []
        )
        secret_key = "my-secret"
        attestation = self.engine.generate_attestation(signing_key=secret_key)

        # Tamper with node count
        attestation["node_count"] = 9999

        valid, log = ArchitectureAttestationEngine.verify_attestation(attestation, signing_key=secret_key)
        self.assertFalse(valid)
        self.assertTrue(any("signature mismatch" in line.lower() for line in log))

    def test_layer_boundary_violation_flagged(self):
        """Lower tier (Tier 3) importing higher tier (Tier 1) must be flagged as violation."""
        nodes = [
            Node(id="fn:core", name="core_sym", node_type=NodeType.FUNCTION, path="agtoosa/core/model.py"),
            Node(id="fn:cli", name="cli_sym", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py"),
        ]
        edges = [
            Edge(source_id="fn:core", target_id="fn:cli", edge_type=EdgeType.IMPORTS),
        ]
        self.store.insert_batch(nodes, edges)

        attestation = self.engine.generate_attestation()
        self.assertEqual(attestation["violations_count"], 1)
        self.assertEqual(len(attestation["blinded_violations"]), 1)

        valid, log = ArchitectureAttestationEngine.verify_attestation(attestation)
        self.assertFalse(valid)
        self.assertTrue(any("layer boundary violation" in line.lower() for line in log))

    def test_mcp_server_attestation_tools(self):
        """MCP server must expose agtoosa_generate_attestation and agtoosa_verify_attestation."""
        self.store.insert_batch(
            [Node(id="fn:mcp", name="mcp_test", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py")],
            []
        )

        server = MCPServer(self.workspace_root)
        server.store = self.store

        # Tool 1: Generate
        gen_resp = server.handle_tool_call("agtoosa_generate_attestation", {"signing_key": "test-key"})
        gen_data = json.loads(gen_resp)
        self.assertEqual(gen_data["version"], "1.0")
        self.assertIsNotNone(gen_data["merkle_root"])

        # Tool 2: Verify
        ver_resp = server.handle_tool_call("agtoosa_verify_attestation", {
            "attestation": gen_data,
            "signing_key": "test-key"
        })
        ver_data = json.loads(ver_resp)
        self.assertTrue(ver_data["valid"])

    def test_cli_attest_generate_and_verify(self):
        """CLI agtoosa attest generate and verify commands must work end-to-end."""
        agtoosa_dir = self.workspace_root / ".agtoosa"
        agtoosa_dir.mkdir(parents=True, exist_ok=True)
        live_db = agtoosa_dir / "graph.db"
        live_store = GraphStore(live_db)
        live_store.insert_batch(
            [Node(id="f:main", name="main", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py")],
            []
        )

        cert_file = self.workspace_root / "cert.json"

        # 1. Generate via CLI
        code_gen = main([
            "-C", str(self.workspace_root),
            "attest", "generate",
            "--output", str(cert_file),
            "--key", "cli-key-456",
            "--json"
        ])
        self.assertEqual(code_gen, 0)
        self.assertTrue(cert_file.exists())

        # 2. Verify via CLI
        code_ver = main([
            "-C", str(self.workspace_root),
            "attest", "verify",
            str(cert_file),
            "--key", "cli-key-456",
            "--json"
        ])
        self.assertEqual(code_ver, 0)


if __name__ == "__main__":
    unittest.main()
