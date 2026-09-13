# Specification: DEV-026 Async Message Queue & Event Bus Lineage

## Status
Approved / In Progress

## Priority Score
**85 / 100** (High Impact — Bridges the decoupled distributed systems boundary across message brokers, event buses, and asynchronous background tasks)

## Problem Statement
In modern microservices and distributed modular architectures, services and modules do not just interact through synchronous HTTP/gRPC calls (addressed in DEV-025); they heavily communicate via asynchronous messaging patterns:
- **Kafka & Event Hubs**: Producers emit events to topics; multiple independent consumer groups process them downstream.
- **RabbitMQ & AMQP**: Producers route messages through exchanges and routing keys into queues consumed by worker pools.
- **Redis Pub/Sub**: Light-weight, high-frequency pub/sub channels coordinating services.
- **Celery & BullMQ**: Distributed task queues where business logic triggers `.delay()` or `.apply_async()`, executed in separate worker processes.

Currently, static analyzers lose all call graph edges at the boundary of `producer.send()` or `task.delay()`. The graph breaks, obscuring:
1. **Hidden blast radius**: Changing the payload schema produced to topic `orders.v2` silently breaks consumers in other modules or repositories.
2. **Dead topics & orphan consumers**: Finding topics that have consumers but no active producers, or published events with no consumers.
3. **End-to-end async trace**: Tracing an action from an HTTP route -> producer -> topic -> consumer -> database write.

## Objectives
1. **Core Domain Ontology Extension**:
   - Introduce `NodeType.TOPIC = "topic"` representing a named message queue, stream, pub/sub channel, or task queue.
   - Introduce `EdgeType.PUBLISHES = "publishes"` linking a Function/Method/Endpoint to a Topic.
   - Introduce `EdgeType.SUBSCRIBES = "subscribes"` linking a Function/Method/Worker to a Topic.
2. **Multi-Ecosystem Extractors (Python & TypeScript/JavaScript)**:
   - **Kafka**:
     - Python: `KafkaProducer.send("topic", ...)`, `producer.produce("topic", ...)`, `KafkaConsumer("topic", ...)`, `AIOKafkaConsumer("topic", ...)`.
     - JS/TS: `producer.send({ topic: '...', ... })`, `consumer.subscribe({ topic: '...', ... })`.
   - **RabbitMQ / AMQP**:
     - Python: `channel.basic_publish(..., routing_key="...")`, `channel.basic_consume(queue="...")`.
     - JS/TS: `channel.sendToQueue("...", ...)`, `channel.publish("...", routingKey, ...)`, `channel.consume("...", ...)`.
   - **Redis Pub/Sub**:
     - Python: `redis.publish("channel", ...)`, `pubsub.subscribe("channel")`.
     - JS/TS: `redis.publish("channel", ...)`, `redis.subscribe("channel")`.
   - **Background Queues (Celery & BullMQ)**:
     - Celery (Python): `@app.task`, `@shared_task`, `task.delay(...)`, `task.apply_async(queue="...")`.
     - BullMQ (JS/TS): `new Queue('queue_name')`, `queue.add('name', ...)`, `new Worker('queue_name', ...)`.
3. **Graph Storage & Query Capabilities**:
   - Storage of Topic nodes and `publishes` / `subscribes` relationships in SQLite graph store.
   - `query_events(store, topic: str | None = None) -> dict`: Returns all topics, their producers, their consumers, and disconnected orphan topics/producers/consumers.
4. **CLI Integration**:
   - `agtoosa graph events [-C <workspace>] [--topic <name>] [--json]` with human-readable colored terminal output and raw JSON dump.
5. **MCP Integration**:
   - Tool `agtoosa_get_event_lineage(topic: str | None = None)` giving AI agents full visibility into asynchronous event flows and blast radius.
6. **Zero Dependencies**:
   - Implemented using Python's standard `ast` and regex parsers. Zero runtime dependencies.

## Architecture & Data Flow

```
[ Code Files (.py, .ts, .js) ]
              │
              ▼
   [ Framework & Event Extractor ]
              │
  Extracts Topic Nodes, PUBLISHES Edges, SUBSCRIBES Edges
              │
              ▼
    [ SQLite Graph Storage ]
              │
     ┌────────┴─────────┐
     ▼                  ▼
[ CLI 'graph events' ]  [ MCP 'agtoosa_get_event_lineage' ]
```

## Verification & Test Plan
- Unit tests in `tests/test_event_lineage.py`:
  - Test Kafka producer/consumer in Python & JS/TS.
  - Test RabbitMQ routing in Python & JS/TS.
  - Test Redis Pub/Sub in Python & JS/TS.
  - Test Celery task definition and `.delay()` invocation.
  - Test `agtoosa graph events` CLI command and JSON output.
  - Test `agtoosa_get_event_lineage` MCP tool.
- All existing 164 unit tests must remain 100% passing.
