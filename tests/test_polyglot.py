"""Tests for Broad Polyglot Coverage (DEV-006)."""

from pathlib import Path
import pytest

from agtoosa.parser.polyglot_parser import PolyglotParser
from agtoosa.core.model import NodeType, EdgeType
from agtoosa.parser import ParserEngine
from agtoosa.graph.store import GraphStore


def test_go_parsing(tmp_path: Path):
    go_file = tmp_path / "server.go"
    go_file.write_text(
        """package main

import (
    "fmt"
    "net/http"
)

type ServerConfig struct {
    Port int
}

type Router interface {
    Route(path string)
}

func StartServer(cfg ServerConfig) {
    fmt.Println("Listening...")
}
""",
        encoding="utf-8"
    )

    parser = PolyglotParser()
    assert parser.can_parse(go_file) is True

    nodes, edges = parser.parse(go_file, tmp_path)
    node_names = {n.name: n for n in nodes}

    assert "server.go" in node_names
    assert "net/http" in node_names
    assert node_names["net/http"].node_type == NodeType.IMPORT

    assert "ServerConfig" in node_names
    assert node_names["ServerConfig"].node_type == NodeType.CLASS
    assert node_names["ServerConfig"].metadata.get("kind") == "struct"

    assert "Router" in node_names
    assert node_names["Router"].node_type == NodeType.CLASS
    assert node_names["Router"].metadata.get("kind") == "interface"

    assert "StartServer" in node_names
    assert node_names["StartServer"].node_type == NodeType.FUNCTION


def test_rust_parsing(tmp_path: Path):
    rs_file = tmp_path / "lib.rs"
    rs_file.write_text(
        """use std::collections::HashMap;

pub struct Client {
    id: u64,
}

pub enum State {
    Init,
    Running,
}

pub trait Worker {
    fn work(&self);
}

pub async fn execute_task(c: &Client) {
    // run
}

impl Worker for Client {
    // impl
}
""",
        encoding="utf-8"
    )

    parser = PolyglotParser()
    assert parser.can_parse(rs_file) is True

    nodes, edges = parser.parse(rs_file, tmp_path)
    node_names = {n.name: n for n in nodes}

    assert "std::collections::HashMap" in node_names
    assert "Client" in node_names
    assert node_names["Client"].metadata.get("kind") == "struct"
    assert "State" in node_names
    assert node_names["State"].metadata.get("kind") == "enum"
    assert "Worker" in node_names
    assert node_names["Worker"].metadata.get("kind") == "trait"
    assert "execute_task" in node_names
    assert node_names["execute_task"].node_type == NodeType.FUNCTION

    # Check implements edge
    impl_edges = [e for e in edges if e.edge_type == EdgeType.IMPLEMENTS]
    assert len(impl_edges) == 1
    assert impl_edges[0].target_id == "class:Worker"


def test_java_and_kotlin_parsing(tmp_path: Path):
    java_file = tmp_path / "UserService.java"
    java_file.write_text(
        """package com.example.service;

import com.example.model.User;
import java.util.List;

public class UserService extends BaseService implements IUserService {
    public User findUser(String id) {
        return null;
    }
}
""",
        encoding="utf-8"
    )

    kt_file = tmp_path / "App.kt"
    kt_file.write_text(
        """package com.example

import kotlinx.coroutines.*

class TaskRunner(val name: String) : BaseRunner {
    fun execute() {
        println("running")
    }
}
""",
        encoding="utf-8"
    )

    parser = PolyglotParser()
    assert parser.can_parse(java_file) is True
    assert parser.can_parse(kt_file) is True

    # Java assertions
    j_nodes, j_edges = parser.parse(java_file, tmp_path)
    j_names = {n.name: n for n in j_nodes}
    assert "UserService" in j_names
    assert "findUser" in j_names
    inherits_edges = [e for e in j_edges if e.edge_type == EdgeType.INHERITS]
    assert any(e.target_id == "class:BaseService" for e in inherits_edges)

    # Kotlin assertions
    k_nodes, k_edges = parser.parse(kt_file, tmp_path)
    k_names = {n.name: n for n in k_nodes}
    assert "TaskRunner" in k_names
    assert "execute" in k_names


def test_cpp_and_csharp_parsing(tmp_path: Path):
    cpp_file = tmp_path / "engine.cpp"
    cpp_file.write_text(
        """#include <iostream>
#include "engine.h"

class PhysicsEngine : public BaseEngine {
    void simulate(float dt) {
        // step
    }
};
""",
        encoding="utf-8"
    )

    cs_file = tmp_path / "Program.cs"
    cs_file.write_text(
        """using System;
using System.Threading.Tasks;

public class Program {
    public static void Main(string[] args) {
        Console.WriteLine("Hello C#");
    }
}
""",
        encoding="utf-8"
    )

    parser = PolyglotParser()
    assert parser.can_parse(cpp_file) is True
    assert parser.can_parse(cs_file) is True

    c_nodes, c_edges = parser.parse(cpp_file, tmp_path)
    c_names = {n.name: n for n in c_nodes}
    assert "engine.h" in c_names
    assert "PhysicsEngine" in c_names
    assert "simulate" in c_names

    cs_nodes, cs_edges = parser.parse(cs_file, tmp_path)
    cs_names = {n.name: n for n in cs_nodes}
    assert "System" in cs_names
    assert "Program" in cs_names
    assert "Main" in cs_names


def test_sql_and_dockerfile_parsing(tmp_path: Path):
    sql_file = tmp_path / "schema.sql"
    sql_file.write_text(
        """CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    user_id INT REFERENCES users(id)
);

CREATE VIEW active_users AS
SELECT * FROM users;
""",
        encoding="utf-8"
    )

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        """FROM golang:1.22 AS builder
WORKDIR /app
COPY . .
RUN go build -o server .

FROM alpine:latest
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
""",
        encoding="utf-8"
    )

    parser = PolyglotParser()
    assert parser.can_parse(sql_file) is True
    assert parser.can_parse(dockerfile) is True

    s_nodes, s_edges = parser.parse(sql_file, tmp_path)
    s_names = {n.name: n for n in s_nodes}
    assert "users" in s_names
    assert s_names["users"].metadata.get("kind") == "table"
    assert "orders" in s_names
    assert "active_users" in s_names
    assert s_names["active_users"].metadata.get("kind") == "view"

    d_nodes, d_edges = parser.parse(dockerfile, tmp_path)
    d_names = {n.name: n for n in d_nodes}
    assert "golang:1.22" in d_names
    assert "alpine:latest" in d_names
    assert "builder" in d_names


def test_engine_polyglot_integration(tmp_path: Path):
    ws = tmp_path / "polyglot_ws"
    ws.mkdir()

    (ws / "main.go").write_text(
        """package main
type Gateway struct {}
func Route() {}
""",
        encoding="utf-8"
    )

    (ws / "schema.sql").write_text(
        """CREATE TABLE accounts (id INT);
""",
        encoding="utf-8"
    )

    db_path = tmp_path / "polyglot.db"
    store = GraphStore(db_path)
    engine = ParserEngine()

    stats = engine.index_workspace(ws, store, clean=True)
    assert stats.total_nodes >= 4  # file:main.go, class:main.go:Gateway, func:main.go:Route, file:schema.sql, class:schema.sql:accounts
    assert stats.files_indexed == 2
