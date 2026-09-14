# DEV-039: Autonomous Cross-Language Microservice Synthesis

> **Cycle:** DEV-039  
> **Milestone:** Milestone 15 (v0.9.0)  
> **Status:** Implemented & Verified  
> **Type:** Federation & Multi-Language Generation  

---

## 1. Problem Statement

Modern microservice architectures are distributed across polyglot codebases (Python, TypeScript/Node.js, Go). When building or refactoring services:
1. **Contract Inconsistency**: API endpoints (REST routes, RPC calls) evolve in code without synchronized interface definitions (OpenAPI specs or Protobuf definitions).
2. **Boilerplate Duplication**: Engineers spend significant time manually writing redundant client SDKs and server stubs across multiple target languages.
3. **Cross-Service Drift**: Federated dependencies between services (DEV-015) drift out of sync when backend endpoints change without updating consumer adapters.

Agtoosa2's knowledge graph already extracts and indexes framework routes (FastAPI, Flask, Express, NestJS in DEV-025), gRPC definitions (DEV-015), and schema models. **DEV-039** transforms this rich architectural graph into an autonomous code generation engine that synthesizes strongly-typed gRPC `.proto` contracts, OpenAPI 3.0 specifications, and cross-language client/server boilerplate in Python, TypeScript, and Go.

---

## 2. Invariants & Synthesis Engine Architecture

### 2.1 Graph Endpoint & Schema Extraction
The engine queries the knowledge graph for:
- **Endpoints**: `NodeType.FUNCTION` nodes with metadata `kind="rest_endpoint"`, `protocol="rest"`, or `method` (GET, POST, PUT, DELETE, etc.), or `protocol="grpc"`.
- **Schemas**: `NodeType.CLASS` / `NodeType.SCHEMA` / ORM models associated with endpoints or in the service namespace.

### 2.2 Protocol Buffers v3 Synthesis
Generates production-grade `syntax = "proto3";`:
- Namespaced package declaration: `package <service_name>.v1;`
- Clean message definitions for request and response payloads, converting standard types (`str` $\to$ `string`, `int` $\to$ `int64`, `bool` $\to$ `bool`, `float` $\to$ `double`, `list` $\to$ `repeated`).
- Service declaration with RPC methods:
  ```protobuf
  service OrderService {
    rpc GetOrder (GetOrderRequest) returns (GetOrderResponse);
  }
  ```

### 2.3 OpenAPI 3.0.3 Specification Synthesis
Generates structured OpenAPI 3.0 JSON / YAML specifications:
- Document header (`openapi: "3.0.3"`, `info.title`, `info.version`).
- `paths`: Path items keyed by route path (e.g. `/api/v1/users/{id}`), with operations, tags, summary, path parameters, and request/response schema references.
- `components.schemas`: Object schemas matching discovered models.

### 2.4 Multi-Language Adapter Generation
- **Python**:
  - Server: FastAPI `APIRouter` with annotated handler signatures and status codes.
  - Client: Async `httpx.AsyncClient` wrapper class with method calls for each endpoint.
- **TypeScript**:
  - Server: Express `Router` with request handlers.
  - Client: Typed `fetch` client class with TypeScript `interface` types.
- **Go**:
  - Server: `net/http` handler functions registered to `http.NewServeMux()`.
  - Client: Struct client with `net/http.Client` helper methods.

---

## 3. Surface Area & Interfaces

### 3.1 Python Engine (`agtoosa/federation/synthesis.py`)
- `MicroserviceSynthesizer`:
  - `__init__(store: GraphStore, workspace_root: Optional[Path] = None)`
  - `discover_service_endpoints(service_name: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]`
  - `synthesize_proto(service_name: str, endpoints: List[Dict[str, Any]], schemas: Optional[List[Dict[str, Any]]] = None) -> str`
  - `synthesize_openapi(service_name: str, endpoints: List[Dict[str, Any]], schemas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`
  - `synthesize_server_adapter(target_lang: str, service_name: str, endpoints: List[Dict[str, Any]]) -> str`
  - `synthesize_client_adapter(target_lang: str, service_name: str, endpoints: List[Dict[str, Any]]) -> str`
  - `synthesize_microservice_bundle(service_name: str, output_dir: Path, target_lang: str = "python", format: str = "all") -> Dict[str, str]`

### 3.2 CLI Interface (`agtoosa/cli/synthesize_cmd.py`)
- `agtoosa synthesize microservice [--service <name>] [--target python|typescript|go] [--format proto|openapi|code|all] [--output <dir>] [--json]`

### 3.3 MCP Tool (`agtoosa/mcp/server.py`)
- `agtoosa_synthesize_microservice`:
  - Parameters: `service_name`, `target_lang`, `format`, `output_dir`.
  - Returns generated file paths and code previews.

---

## 4. Verification & Testing Strategy
- Unit tests in `tests/test_synthesis.py`:
  - Verify endpoint and schema discovery from graph store.
  - Verify syntax and completeness of generated `.proto` definitions.
  - Verify structure and validation of generated OpenAPI 3.0 JSON.
  - Verify syntax and idioms of generated Python, TypeScript, and Go adapters.
  - Verify CLI and MCP end-to-end invocations.
