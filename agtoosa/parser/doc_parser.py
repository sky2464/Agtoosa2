"""Parser for Agtoosa specifications, ADRs, and lifecycle markdown artifacts."""

import re
from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.parser.base import BaseParser


class MarkdownDocParser(BaseParser):
    """Extracts Story, Criterion, Task, and ADR entities from documentation."""

    STORY_HEADER_REGEX = re.compile(
        r"^#\s+(?:(?:Spec(?:ification)?|Story|Epic):\s*|(?:DEV-\d+):\s*|(?:EPIC-\d+):\s*|Epic\s+)?(DEV-\d+|EPIC-\d+)(?:[:\s—\-]+)(.+)$",
        re.MULTILINE
    )
    CRITERION_REGEX = re.compile(r"^-\s+\*\*(AC-?[\d.]+)\s*(?:\([^)]+\))?\*\*:\s*(.+)$", re.MULTILINE)
    TABLE_CRITERION_REGEX = re.compile(r"^\|\s*(AC-?\d+)\s*\|\s*([^|]+)\s*\|", re.MULTILINE)
    TASK_REGEX = re.compile(r"^-\s+\[([ xX])\]\s+(?:(?:\*\*(Task\s+[\d.]+)\*\*:\s*(.+))|([^\n]+))$", re.MULTILINE)
    ADR_HEADER_REGEX = re.compile(r"^#\s+\[(ADR-\d+)\]\s+(.+)$", re.MULTILINE)
    STATUS_REGEX = re.compile(
        r"(?:(?:^>|\n>|\n|^)\s*\*\*Status:\*\*\s*([^\n]+)|(?:^##\s*Status\s*\n+([^\n]+)))",
        re.IGNORECASE | re.MULTILINE
    )
    MILESTONE_REGEX = re.compile(r"(?:>|\n>)\s*\*\*Milestone:\*\*\s*([^\n]+)", re.IGNORECASE)

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".md", ".markdown")

    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        rel_path = str(file_path.relative_to(workspace_root))
        file_node_id = f"file:{rel_path}"

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return nodes, edges

        lines = content.splitlines()

        # Base File Node
        nodes.append(
            Node(
                id=file_node_id,
                name=file_path.name,
                node_type=NodeType.DOC,
                path=rel_path,
                metadata={"total_lines": len(lines)}
            )
        )

        # 1. Check for Story Spec (docs/specs/spec-DEV-*.md)
        story_match = self.STORY_HEADER_REGEX.search(content)
        if story_match:
            story_id_num = story_match.group(1)  # e.g. DEV-001
            story_title = story_match.group(2).strip()
            story_title = re.sub(r"^[—\-:\s]+", "", story_title).strip()
            story_node_id = f"story:{story_id_num}"

            # Extract Status & Milestone
            status_match = self.STATUS_REGEX.search(content)
            status_val = ""
            if status_match:
                raw_stat = (status_match.group(1) or status_match.group(2) or "").strip()
                s = re.sub(r"^[-*>\s]+", "", raw_stat)
                status_val = re.sub(r"^(?:\*\*)?Status:(?:\*\*)?\s*", "", s, flags=re.IGNORECASE).strip()

            milestone_match = self.MILESTONE_REGEX.search(content)
            milestone_val = milestone_match.group(1).strip() if milestone_match else ""

            # Story Node
            nodes.append(
                Node(
                    id=story_node_id,
                    name=f"{story_id_num}: {story_title}",
                    node_type=NodeType.STORY,
                    path=rel_path,
                    start_line=1,
                    metadata={
                        "story_id": story_id_num,
                        "title": story_title,
                        "status": status_val,
                        "milestone": milestone_val,
                    }
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=story_node_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

            # Extract Acceptance Criteria (Bulleted or Table)
            crit_seen = set()
            for crit_match in self.CRITERION_REGEX.finditer(content):
                crit_code = crit_match.group(1)  # e.g. AC-1
                crit_text = crit_match.group(2).strip()
                crit_seen.add(crit_code)
                crit_node_id = f"criterion:{story_id_num}:{crit_code}"
                line_idx = content[: crit_match.start()].count("\n") + 1

                nodes.append(
                    Node(
                        id=crit_node_id,
                        name=f"{story_id_num} {crit_code}",
                        node_type=NodeType.CRITERION,
                        path=rel_path,
                        start_line=line_idx,
                        docstring=crit_text,
                        metadata={"criterion_code": crit_code}
                    )
                )
                edges.append(
                    Edge(
                        source_id=story_node_id,
                        target_id=crit_node_id,
                        edge_type=EdgeType.DEFINES
                    )
                )

            for table_match in self.TABLE_CRITERION_REGEX.finditer(content):
                crit_code = table_match.group(1)  # e.g. AC-01
                crit_text = table_match.group(2).strip()
                if crit_code in crit_seen:
                    continue
                crit_seen.add(crit_code)
                crit_node_id = f"criterion:{story_id_num}:{crit_code}"
                line_idx = content[: table_match.start()].count("\n") + 1

                nodes.append(
                    Node(
                        id=crit_node_id,
                        name=f"{story_id_num} {crit_code}",
                        node_type=NodeType.CRITERION,
                        path=rel_path,
                        start_line=line_idx,
                        docstring=crit_text,
                        metadata={"criterion_code": crit_code}
                    )
                )
                edges.append(
                    Edge(
                        source_id=story_node_id,
                        target_id=crit_node_id,
                        edge_type=EdgeType.DEFINES
                    )
                )

            # Extract Tasks
            for idx, task_match in enumerate(self.TASK_REGEX.finditer(content), start=1):
                is_checked = task_match.group(1).lower() == "x"
                if task_match.group(2):
                    task_code = task_match.group(2).strip()  # e.g. Task 1.1
                    task_desc = (task_match.group(3) or "").strip()
                else:
                    task_code = f"Task {idx}"
                    task_desc = (task_match.group(4) or "").strip()
                task_node_id = f"task:{story_id_num}:{task_code.replace(' ', '_')}"
                line_idx = content[: task_match.start()].count("\n") + 1

                nodes.append(
                    Node(
                        id=task_node_id,
                        name=f"{story_id_num} {task_code}",
                        node_type=NodeType.TASK,
                        path=rel_path,
                        start_line=line_idx,
                        docstring=task_desc,
                        metadata={"completed": is_checked}
                    )
                )
                edges.append(
                    Edge(
                        source_id=story_node_id,
                        target_id=task_node_id,
                        edge_type=EdgeType.CONTAINS
                    )
                )

        # 2. Check for ADR (docs/adr/ADR-*.md)
        adr_match = self.ADR_HEADER_REGEX.search(content)
        if adr_match:
            adr_code = adr_match.group(1)  # e.g. ADR-001
            adr_title = adr_match.group(2).strip()
            adr_node_id = f"adr:{adr_code}"

            nodes.append(
                Node(
                    id=adr_node_id,
                    name=f"{adr_code}: {adr_title}",
                    node_type=NodeType.ADR,
                    path=rel_path,
                    start_line=1,
                    docstring=content[:300],
                    metadata={"adr_id": adr_code}
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=adr_node_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

        return nodes, edges
