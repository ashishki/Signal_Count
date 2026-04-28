"""Workflow graph declarations for bounded orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NodeType = Literal["specialist", "verifier", "coordinator"]


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: NodeType
    optional: bool = False


@dataclass(frozen=True)
class WorkflowGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("workflow graph node ids must be unique")
        known = set(node_ids)
        for source, target in self.edges:
            if source not in known or target not in known:
                raise ValueError("workflow graph edge references unknown node")
        _assert_acyclic(node_ids=node_ids, edges=self.edges)

    @property
    def specialist_roles(self) -> tuple[str, ...]:
        return tuple(node.id for node in self.nodes if node.type == "specialist")

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": [
                {"id": node.id, "type": node.type, "optional": node.optional}
                for node in self.nodes
            ],
            "edges": [list(edge) for edge in self.edges],
        }


def _assert_acyclic(
    *,
    node_ids: list[str],
    edges: tuple[tuple[str, str], ...],
) -> None:
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    for source, target in edges:
        outgoing[source].append(target)
        indegree[target] += 1

    ready = [node_id for node_id in node_ids if indegree[node_id] == 0]
    visited = 0
    while ready:
        node_id = ready.pop(0)
        visited += 1
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)

    if visited != len(node_ids):
        raise ValueError("workflow graph must be acyclic")


DEFAULT_WORKFLOW_GRAPH = WorkflowGraph(
    nodes=(
        GraphNode(id="regime", type="specialist"),
        GraphNode(id="narrative", type="specialist"),
        GraphNode(id="risk", type="specialist"),
        GraphNode(id="verifier", type="verifier"),
        GraphNode(id="synthesis", type="coordinator"),
    ),
    edges=(
        ("regime", "verifier"),
        ("narrative", "verifier"),
        ("risk", "verifier"),
        ("verifier", "synthesis"),
    ),
)
