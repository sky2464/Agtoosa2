"""Event Lineage and Message Queue extractors for Agtoosa2.

Extracts Topics, Publishers, and Subscribers for:
- Kafka (Python & TS/JS)
- RabbitMQ / AMQP (Python & TS/JS)
- Redis Pub/Sub (Python & TS/JS)
- Distributed Task Queues (Celery in Python, BullMQ in TS/JS)
"""

from __future__ import annotations
import ast
import re
from typing import List, Tuple, Optional, Set
from agtoosa.core.model import Node, Edge, NodeType, EdgeType


class PythonEventExtractor:
    """Extracts async event publish/subscribe semantics from Python AST."""

    @classmethod
    def extract(
        cls,
        tree: ast.AST,
        rel_path: str,
        file_node_id: str
    ) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []
        seen_topics: Set[str] = set()
        celery_task_names: dict[str, str] = {}

        # Pre-scan Celery task functions to resolve alias names
        for item in ast.walk(tree):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in item.decorator_list:
                    dec_name = ""
                    custom_name = None
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name):
                            dec_name = dec.func.id
                        elif isinstance(dec.func, ast.Attribute):
                            dec_name = dec.func.attr
                        for kw in dec.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                custom_name = str(kw.value.value)
                    if dec_name in ("task", "shared_task"):
                        celery_task_names[item.name] = custom_name or f"celery:{item.name}"

        def _get_or_create_topic(topic_name: str, broker: str, line_no: int = 1) -> str:
            topic_id = f"topic:{topic_name}"
            if topic_id not in seen_topics:
                seen_topics.add(topic_id)
                nodes.append(
                    Node(
                        id=topic_id,
                        name=topic_name,
                        node_type=NodeType.TOPIC,
                        path=rel_path,
                        start_line=line_no,
                        metadata={"topic": topic_name, "broker": broker}
                    )
                )
            return topic_id

        class EventVisitor(ast.NodeVisitor):
            def __init__(self):
                self.scope_stack: List[str] = [file_node_id]

            def visit_ClassDef(self, node: ast.ClassDef):
                class_id = f"class:{rel_path}:{node.name}"
                self.scope_stack.append(class_id)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_function(node)

            def _handle_function(self, node):
                parent = self.scope_stack[-1]
                func_id = (
                    f"func:{rel_path}:{parent.split(':')[-1]}.{node.name}"
                    if parent != file_node_id
                    else f"func:{rel_path}:{node.name}"
                )

                # Check for Celery / Task decorators: @app.task, @shared_task, @celery.task
                for dec in node.decorator_list:
                    dec_name = ""
                    dec_args = {}
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name):
                            dec_name = dec.func.id
                        elif isinstance(dec.func, ast.Attribute):
                            dec_name = dec.func.attr
                        for kw in dec.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                dec_args["name"] = str(kw.value.value)

                    if dec_name in ("task", "shared_task"):
                        task_name = celery_task_names.get(node.name, f"celery:{node.name}")
                        topic_id = _get_or_create_topic(task_name, broker="celery", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=func_id,
                                target_id=topic_id,
                                edge_type=EdgeType.SUBSCRIBES,
                                metadata={"broker": "celery", "task": node.name}
                            )
                        )

                self.scope_stack.append(func_id)
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Call(self, node: ast.Call):
                current_scope = self.scope_stack[-1]
                self._check_call_events(node, current_scope)
                self.generic_visit(node)

            def _check_call_events(self, node: ast.Call, current_scope: str):
                func = node.func
                method_name = ""
                caller_expr = ""

                if isinstance(func, ast.Attribute):
                    method_name = func.attr
                    if isinstance(func.value, ast.Name):
                        caller_expr = func.value.id
                    elif hasattr(ast, "unparse"):
                        try:
                            caller_expr = ast.unparse(func.value)
                        except Exception:
                            caller_expr = ""
                elif isinstance(func, ast.Name):
                    method_name = func.id

                # 1. Celery task invocation: task.delay(...) or task.apply_async(...)
                if method_name in ("delay", "apply_async") and caller_expr:
                    task_name = celery_task_names.get(caller_expr, f"celery:{caller_expr}")
                    # Check if explicit queue or routing_key provided in apply_async
                    queue_name = None
                    if method_name == "apply_async":
                        for kw in node.keywords:
                            if kw.arg in ("queue", "routing_key") and isinstance(kw.value, ast.Constant):
                                queue_name = str(kw.value.value)
                    target_topic_name = queue_name if queue_name else task_name
                    topic_id = _get_or_create_topic(target_topic_name, broker="celery", line_no=node.lineno)
                    edges.append(
                        Edge(
                            source_id=current_scope,
                            target_id=topic_id,
                            edge_type=EdgeType.PUBLISHES,
                            metadata={"broker": "celery", "task": caller_expr, "method": method_name}
                        )
                    )
                    return

                # 2. Kafka send / produce
                # e.g., producer.send("orders", ...), producer.produce(topic="orders", ...)
                if method_name in ("send", "produce", "send_and_wait"):
                    topic_val = None
                    for kw in node.keywords:
                        if kw.arg == "topic" and isinstance(kw.value, ast.Constant):
                            topic_val = str(kw.value.value)
                    if not topic_val and node.args and isinstance(node.args[0], ast.Constant):
                        topic_val = str(node.args[0].value)

                    if topic_val:
                        topic_id = _get_or_create_topic(topic_val, broker="kafka", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.PUBLISHES,
                                metadata={"broker": "kafka", "method": method_name}
                            )
                        )
                        return

                # 3. Kafka Consumer
                # e.g., KafkaConsumer("orders"), AIOKafkaConsumer("orders", ...)
                if method_name in ("KafkaConsumer", "AIOKafkaConsumer"):
                    topics: List[str] = []
                    if node.args:
                        if isinstance(node.args[0], ast.Constant):
                            topics.append(str(node.args[0].value))
                        elif isinstance(node.args[0], (ast.List, ast.Tuple)):
                            for el in node.args[0].elts:
                                if isinstance(el, ast.Constant):
                                    topics.append(str(el.value))
                    for kw in node.keywords:
                        if kw.arg in ("topics", "topic"):
                            if isinstance(kw.value, ast.Constant):
                                topics.append(str(kw.value.value))
                            elif isinstance(kw.value, (ast.List, ast.Tuple)):
                                for el in kw.value.elts:
                                    if isinstance(el, ast.Constant):
                                        topics.append(str(el.value))

                    for top in topics:
                        topic_id = _get_or_create_topic(top, broker="kafka", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.SUBSCRIBES,
                                metadata={"broker": "kafka", "method": method_name}
                            )
                        )
                    return

                # 4. RabbitMQ basic_publish
                if method_name == "basic_publish":
                    routing_key = None
                    for kw in node.keywords:
                        if kw.arg == "routing_key" and isinstance(kw.value, ast.Constant):
                            routing_key = str(kw.value.value)
                    if not routing_key and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                        routing_key = str(node.args[1].value)

                    if routing_key:
                        topic_id = _get_or_create_topic(routing_key, broker="rabbitmq", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.PUBLISHES,
                                metadata={"broker": "rabbitmq", "routing_key": routing_key}
                            )
                        )
                    return

                # 5. RabbitMQ basic_consume
                if method_name == "basic_consume":
                    queue_val = None
                    callback_name = None
                    for kw in node.keywords:
                        if kw.arg == "queue" and isinstance(kw.value, ast.Constant):
                            queue_val = str(kw.value.value)
                        elif kw.arg == "on_message_callback" and isinstance(kw.value, ast.Name):
                            callback_name = kw.value.id

                    if not queue_val and node.args and isinstance(node.args[0], ast.Constant):
                        queue_val = str(node.args[0].value)

                    if queue_val:
                        topic_id = _get_or_create_topic(queue_val, broker="rabbitmq", line_no=node.lineno)
                        subscriber_id = (
                            f"func:{rel_path}:{callback_name}" if callback_name else current_scope
                        )
                        edges.append(
                            Edge(
                                source_id=subscriber_id,
                                target_id=topic_id,
                                edge_type=EdgeType.SUBSCRIBES,
                                metadata={"broker": "rabbitmq", "queue": queue_val}
                            )
                        )
                    return

                # 6. Redis publish / subscribe
                if method_name == "publish" and (caller_expr in ("r", "redis", "client", "redis_client") or "pubsub" in caller_expr):
                    channel_val = None
                    if node.args and isinstance(node.args[0], ast.Constant):
                        channel_val = str(node.args[0].value)
                    for kw in node.keywords:
                        if kw.arg in ("channel", "name") and isinstance(kw.value, ast.Constant):
                            channel_val = str(kw.value.value)

                    if channel_val:
                        topic_id = _get_or_create_topic(channel_val, broker="redis", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.PUBLISHES,
                                metadata={"broker": "redis", "channel": channel_val}
                            )
                        )
                    return

                if method_name in ("subscribe", "psubscribe"):
                    channels: List[str] = []
                    if node.args:
                        if isinstance(node.args[0], ast.Constant):
                            channels.append(str(node.args[0].value))
                        elif isinstance(node.args[0], (ast.List, ast.Tuple)):
                            for el in node.args[0].elts:
                                if isinstance(el, ast.Constant):
                                    channels.append(str(el.value))
                    for kw in node.keywords:
                        if kw.arg in ("channel", "channels"):
                            if isinstance(kw.value, ast.Constant):
                                channels.append(str(kw.value.value))
                            elif isinstance(kw.value, (ast.List, ast.Tuple)):
                                for el in kw.value.elts:
                                    if isinstance(el, ast.Constant):
                                        channels.append(str(el.value))

                    for ch in channels:
                        topic_id = _get_or_create_topic(ch, broker="redis", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.SUBSCRIBES,
                                metadata={"broker": "redis", "channel": ch}
                            )
                        )
                    return

                # 7. AWS SQS send_message / receive_message
                if method_name in ("send_message", "send_message_batch"):
                    queue_val = None
                    for kw in node.keywords:
                        if kw.arg in ("QueueUrl", "queue_url") and isinstance(kw.value, ast.Constant):
                            queue_val = str(kw.value.value).rstrip("/").split("/")[-1]
                    if not queue_val and caller_expr and any(k in caller_expr.lower() for k in ("sqs", "queue")):
                        queue_val = caller_expr
                    if queue_val:
                        topic_id = _get_or_create_topic(queue_val, broker="sqs", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.PUBLISHES,
                                metadata={"broker": "sqs", "method": method_name}
                            )
                        )
                        return

                if method_name in ("receive_message", "receive_messages"):
                    queue_val = None
                    for kw in node.keywords:
                        if kw.arg in ("QueueUrl", "queue_url") and isinstance(kw.value, ast.Constant):
                            queue_val = str(kw.value.value).rstrip("/").split("/")[-1]
                    if not queue_val and caller_expr and any(k in caller_expr.lower() for k in ("sqs", "queue")):
                        queue_val = caller_expr
                    if queue_val:
                        topic_id = _get_or_create_topic(queue_val, broker="sqs", line_no=node.lineno)
                        edges.append(
                            Edge(
                                source_id=current_scope,
                                target_id=topic_id,
                                edge_type=EdgeType.SUBSCRIBES,
                                metadata={"broker": "sqs", "method": method_name}
                            )
                        )
                        return

        visitor = EventVisitor()
        visitor.visit(tree)
        return nodes, edges


class TypeScriptEventExtractor:
    """Extracts async event publish/subscribe semantics from JS/TS source code."""

    KAFKA_PUBLISH_REGEX = re.compile(
        r'\.send\s*\(\s*\{\s*[^}]*topic\s*:\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    KAFKA_SUBSCRIBE_REGEX = re.compile(
        r'\.subscribe\s*\(\s*\{\s*[^}]*topic\s*:\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )

    RABBIT_SEND_QUEUE_REGEX = re.compile(
        r'\.sendToQueue\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    RABBIT_PUBLISH_REGEX = re.compile(
        r'\.publish\s*\([^,]+,\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    RABBIT_CONSUME_REGEX = re.compile(
        r'\.consume\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )

    REDIS_PUBLISH_REGEX = re.compile(
        r'\.publish\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    REDIS_SUBSCRIBE_REGEX = re.compile(
        r'\.subscribe\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )

    BULLMQ_QUEUE_REGEX = re.compile(
        r'new\s+Queue\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    BULLMQ_WORKER_REGEX = re.compile(
        r'new\s+Worker\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    BULLMQ_ADD_REGEX = re.compile(
        r'(\w+)\.add\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )

    SQS_SEND_REGEX = re.compile(
        r'(?:\.sendMessage|\.sendMessageBatch|new\s+SendMessageCommand)\s*\(\s*\{[^}]*QueueUrl\s*:\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )
    SQS_RECEIVE_REGEX = re.compile(
        r'(?:\.receiveMessage|\.receiveMessages|new\s+ReceiveMessageCommand)\s*\(\s*\{[^}]*QueueUrl\s*:\s*[\'"`]([^\'"`]+)[\'"`]',
        re.MULTILINE
    )

    @classmethod
    def extract(
        cls,
        content: str,
        rel_path: str,
        file_node_id: str
    ) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []
        seen_topics: Set[str] = set()

        def _get_or_create_topic(topic_name: str, broker: str, line_no: int = 1) -> str:
            topic_id = f"topic:{topic_name}"
            if topic_id not in seen_topics:
                seen_topics.add(topic_id)
                nodes.append(
                    Node(
                        id=topic_id,
                        name=topic_name,
                        node_type=NodeType.TOPIC,
                        path=rel_path,
                        start_line=line_no,
                        metadata={"topic": topic_name, "broker": broker}
                    )
                )
            return topic_id

        # 1. KafkaJS
        for match in cls.KAFKA_PUBLISH_REGEX.finditer(content):
            topic = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(topic, broker="kafka", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "kafka"}
                )
            )

        for match in cls.KAFKA_SUBSCRIBE_REGEX.finditer(content):
            topic = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(topic, broker="kafka", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.SUBSCRIBES,
                    metadata={"broker": "kafka"}
                )
            )

        # 2. RabbitMQ / amqplib
        for match in cls.RABBIT_SEND_QUEUE_REGEX.finditer(content):
            queue = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue, broker="rabbitmq", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "rabbitmq", "queue": queue}
                )
            )

        for match in cls.RABBIT_PUBLISH_REGEX.finditer(content):
            routing_key = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(routing_key, broker="rabbitmq", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "rabbitmq", "routing_key": routing_key}
                )
            )

        for match in cls.RABBIT_CONSUME_REGEX.finditer(content):
            queue = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue, broker="rabbitmq", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.SUBSCRIBES,
                    metadata={"broker": "rabbitmq", "queue": queue}
                )
            )

        # 3. Redis Pub/Sub
        for match in cls.REDIS_PUBLISH_REGEX.finditer(content):
            channel = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(channel, broker="redis", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "redis", "channel": channel}
                )
            )

        for match in cls.REDIS_SUBSCRIBE_REGEX.finditer(content):
            channel = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(channel, broker="redis", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.SUBSCRIBES,
                    metadata={"broker": "redis", "channel": channel}
                )
            )

        # 4. BullMQ
        for match in cls.BULLMQ_WORKER_REGEX.finditer(content):
            queue_name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue_name, broker="bullmq", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.SUBSCRIBES,
                    metadata={"broker": "bullmq", "worker": True}
                )
            )

        for match in cls.BULLMQ_QUEUE_REGEX.finditer(content):
            queue_name = match.group(1)
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue_name, broker="bullmq", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "bullmq", "queue": True}
                )
            )

        # 5. AWS SQS
        for match in cls.SQS_SEND_REGEX.finditer(content):
            raw_url = match.group(1)
            queue_name = raw_url.rstrip("/").split("/")[-1]
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue_name, broker="sqs", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.PUBLISHES,
                    metadata={"broker": "sqs", "queue_url": raw_url}
                )
            )

        for match in cls.SQS_RECEIVE_REGEX.finditer(content):
            raw_url = match.group(1)
            queue_name = raw_url.rstrip("/").split("/")[-1]
            line = content[: match.start()].count("\n") + 1
            top_id = _get_or_create_topic(queue_name, broker="sqs", line_no=line)
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=top_id,
                    edge_type=EdgeType.SUBSCRIBES,
                    metadata={"broker": "sqs", "queue_url": raw_url}
                )
            )

        return nodes, edges
