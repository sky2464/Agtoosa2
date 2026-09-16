"""Automated tests for DEV-026: Async Message Queue and Event Bus Lineage."""

import json
import pytest
from pathlib import Path
from agtoosa.core.model import NodeType, EdgeType
from agtoosa.parser import ParserEngine
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import query_events
from agtoosa.mcp.server import MCPServer
from agtoosa.cli.main import main


def test_python_event_lineage_extraction(tmp_path: Path):
    """Test Python Kafka, RabbitMQ, Redis, and Celery extractors."""
    code = """
import pika
import redis
from kafka import KafkaProducer, KafkaConsumer
from celery import Celery

app = Celery("myapp")

@app.task(name="tasks.send_welcome_email")
def send_welcome_email(user_id):
    pass

@app.task
def process_payment(amount):
    pass

def trigger_events():
    # Celery invocations
    send_welcome_email.delay(123)
    process_payment.apply_async(args=[450], queue="urgent_payments")

    # Kafka produce
    producer = KafkaProducer()
    producer.send("orders.v1", b"payload")

    # RabbitMQ publish
    connection = pika.BlockingConnection()
    channel = connection.channel()
    channel.basic_publish(exchange="", routing_key="notifications", body=b"hello")

    # Redis publish
    r = redis.Redis()
    r.publish("live_chat", "new message")

def listen_events():
    # Kafka consume
    consumer = KafkaConsumer("orders.v1")

    # RabbitMQ consume
    channel.basic_consume(queue="notifications", on_message_callback=handle_notify)

    # Redis subscribe
    pubsub = r.pubsub()
    pubsub.subscribe("live_chat")

def handle_notify(ch, method, properties, body):
    pass
"""
    test_file = tmp_path / "services.py"
    test_file.write_text(code)

    db_path = tmp_path / ".agtoosa" / "graph.db"
    store = GraphStore(db_path)
    engine = ParserEngine()
    result = engine.index_workspace(tmp_path, store, clean=True)

    assert result.files_indexed == 1

    # Check topic nodes
    topics = [n for n in store.get_all_nodes() if n["node_type"] == "topic"]
    topic_names = {t["name"] for t in topics}
    assert "orders.v1" in topic_names
    assert "notifications" in topic_names
    assert "live_chat" in topic_names
    assert "tasks.send_welcome_email" in topic_names
    assert "urgent_payments" in topic_names

    # Check query_events
    ev_data = query_events(store)
    assert ev_data["total_topics"] >= 5
    assert ev_data["total_publishers"] >= 5
    assert ev_data["total_subscribers"] >= 5

    # Check specific Kafka topic
    kafka_ev = query_events(store, topic="orders.v1")
    assert kafka_ev["total_topics"] == 1
    t = kafka_ev["topics"][0]
    assert t["name"] == "orders.v1"
    assert t["broker"] == "kafka"
    assert len(t["publishers"]) >= 1
    assert len(t["subscribers"]) >= 1
    assert not t["is_orphan"]

    # Check Celery task
    celery_ev = query_events(store, topic="tasks.send_welcome_email")
    assert celery_ev["total_topics"] == 1
    ct = celery_ev["topics"][0]
    assert ct["broker"] == "celery"
    assert len(ct["subscribers"]) == 1
    assert ct["subscribers"][0]["node"]["name"] == "send_welcome_email"
    assert len(ct["publishers"]) == 1


def test_typescript_event_lineage_extraction(tmp_path: Path):
    """Test TypeScript/JavaScript KafkaJS, amqplib, Redis, and BullMQ extractors."""
    code = """
import { Kafka } from 'kafkajs';
import amqp from 'amqplib';
import Redis from 'ioredis';
import { Queue, Worker } from 'bullmq';

// KafkaJS
async function runKafka() {
    const producer = kafka.producer();
    await producer.send({
        topic: 'user-signups',
        messages: [{ value: 'user_123' }]
    });

    const consumer = kafka.consumer({ groupId: 'test-group' });
    await consumer.subscribe({ topic: 'user-signups', fromBeginning: true });
}

// RabbitMQ (amqplib)
async function runRabbit(channel) {
    channel.sendToQueue('export_jobs', Buffer.from('data'));
    channel.consume('export_jobs', (msg) => {});
}

// Redis Pub/Sub
function runRedis(redisClient) {
    redisClient.publish('telemetry_stream', JSON.stringify({ ping: true }));
    redisClient.subscribe('telemetry_stream');
}

// BullMQ
const queue = new Queue('billingQueue');
queue.add('chargeUser', { amount: 100 });
const worker = new Worker('billingQueue', async job => {});
"""
    test_file = tmp_path / "events.ts"
    test_file.write_text(code)

    db_path = tmp_path / ".agtoosa" / "graph.db"
    store = GraphStore(db_path)
    engine = ParserEngine()
    result = engine.index_workspace(tmp_path, store, clean=True)

    assert result.files_indexed == 1

    topics = [n for n in store.get_all_nodes() if n["node_type"] == "topic"]
    topic_names = {t["name"] for t in topics}
    assert "user-signups" in topic_names
    assert "export_jobs" in topic_names
    assert "telemetry_stream" in topic_names
    assert "billingQueue" in topic_names

    ev_data = query_events(store)
    assert ev_data["total_topics"] == 4
    # All topics have both publisher and subscriber
    for top in ev_data["topics"]:
        assert len(top["publishers"]) >= 1
        assert len(top["subscribers"]) >= 1
        assert not top["is_orphan"]


def test_orphan_event_detection(tmp_path: Path):
    """Test orphan detection: topics with publishers but no subscribers, or vice versa."""
    code = """
from kafka import KafkaProducer

def publish_dead_letter():
    producer = KafkaProducer()
    producer.send("unconsumed_alerts", b"alert!")
"""
    test_file = tmp_path / "producer_only.py"
    test_file.write_text(code)

    db_path = tmp_path / ".agtoosa" / "graph.db"
    store = GraphStore(db_path)
    engine = ParserEngine()
    engine.index_workspace(tmp_path, store, clean=True)

    ev_data = query_events(store)
    assert ev_data["total_topics"] == 1
    assert ev_data["orphan_count"] == 1
    top = ev_data["topics"][0]
    assert top["is_orphan"] is True
    assert top["orphan_reason"] == "no_subscribers"


def test_cli_graph_events(tmp_path: Path, capsys):
    """Test 'agtoosa graph events' CLI command and JSON format."""
    code = """
from kafka import KafkaProducer, KafkaConsumer

def prod():
    p = KafkaProducer()
    p.send("orders.v1", b"order_data")

def cons():
    c = KafkaConsumer("orders.v1")
"""
    test_file = tmp_path / "app.py"
    test_file.write_text(code)

    # Build graph
    assert main(["-C", str(tmp_path), "graph", "build"]) == 0
    capsys.readouterr()

    # CLI human-readable events
    code_res = main(["-C", str(tmp_path), "graph", "events"])
    assert code_res == 0
    out = capsys.readouterr().out
    assert "Asynchronous Event & Queue Lineage" in out
    assert "[KAFKA]" in out
    assert "orders.v1" in out

    # CLI JSON events
    code_json = main(["-C", str(tmp_path), "graph", "events", "--json"])
    assert code_json == 0
    out_json = capsys.readouterr().out
    data = json.loads(out_json)
    assert data["total_topics"] == 1
    assert data["topics"][0]["name"] == "orders.v1"


def test_mcp_event_lineage(tmp_path: Path):
    """Test MCP tool 'agtoosa_get_event_lineage'."""
    code = """
import redis
r = redis.Redis()
r.publish("presence", "online")
"""
    test_file = tmp_path / "presence.py"
    test_file.write_text(code)

    db_path = tmp_path / ".agtoosa" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_path)
    engine = ParserEngine()
    engine.index_workspace(tmp_path, store, clean=True)

    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_get_event_lineage", {"topic": "presence"})
    res = json.loads(res_str)
    assert res["total_topics"] == 1
    assert res["topics"][0]["name"] == "presence"
    assert res["topics"][0]["broker"] == "redis"


def test_sqs_event_lineage_python_and_ts(tmp_path: Path):
    """Test AWS SQS event publisher and subscriber extraction in Python and TS."""
    py_code = """
import boto3

def send_sqs():
    sqs = boto3.client("sqs")
    sqs.send_message(QueueUrl="https://sqs.us-east-1.amazonaws.com/12345/invoices-queue", MessageBody="inv_1")

def receive_sqs():
    sqs = boto3.client("sqs")
    sqs.receive_message(QueueUrl="https://sqs.us-east-1.amazonaws.com/12345/invoices-queue")
"""
    ts_code = """
import { SendMessageCommand, ReceiveMessageCommand } from "@aws-sdk/client-sqs";

async function pushMsg() {
    new SendMessageCommand({ QueueUrl: "https://sqs.us-east-1.amazonaws.com/12345/audit-log" });
}

async function pullMsg() {
    new ReceiveMessageCommand({ QueueUrl: "https://sqs.us-east-1.amazonaws.com/12345/audit-log" });
}
"""
    (tmp_path / "py_sqs.py").write_text(py_code, encoding="utf-8")
    (tmp_path / "ts_sqs.ts").write_text(ts_code, encoding="utf-8")

    db_path = tmp_path / ".agtoosa" / "graph.db"
    store = GraphStore(db_path)
    engine = ParserEngine()
    engine.index_workspace(tmp_path, store, clean=True)

    ev_inv = query_events(store, topic="invoices-queue")
    assert ev_inv["total_topics"] == 1
    assert ev_inv["topics"][0]["broker"] == "sqs"
    assert len(ev_inv["topics"][0]["publishers"]) == 1
    assert len(ev_inv["topics"][0]["subscribers"]) == 1
    assert not ev_inv["topics"][0]["is_orphan"]

    ev_audit = query_events(store, topic="audit-log")
    assert ev_audit["total_topics"] == 1
    assert ev_audit["topics"][0]["broker"] == "sqs"
    assert len(ev_audit["topics"][0]["publishers"]) == 1
    assert len(ev_audit["topics"][0]["subscribers"]) == 1
    assert not ev_audit["topics"][0]["is_orphan"]


def test_event_lineage_prevents_false_dead_code(tmp_path: Path):
    """Test that event subscribers connected to publishers are not flagged as dead code."""
    code = """
from celery import Celery

app = Celery("app")

@app.task
def process_background_job(data):
    return len(data)

def invoke():
    process_background_job.delay("data")
"""
    (tmp_path / "celery_jobs.py").write_text(code, encoding="utf-8")
    db_path = tmp_path / ".agtoosa" / "graph.db"
    store = GraphStore(db_path)
    engine = ParserEngine()
    engine.index_workspace(tmp_path, store, clean=True)

    from agtoosa.refactor.dead_code import DeadCodePruner
    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    zombie_names = [z.name for z in report.zombies]
    assert "process_background_job" not in zombie_names

