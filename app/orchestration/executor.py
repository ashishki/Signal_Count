"""Bounded execution helpers for workflow graphs."""

from __future__ import annotations

from dataclasses import dataclass

from app.orchestration.graph import WorkflowGraph


@dataclass(frozen=True)
class ExecutionPlan:
    specialist_roles: tuple[str, ...]
    verifier_node_id: str | None
    synthesis_node_id: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "specialist_roles": list(self.specialist_roles),
            "verifier_node_id": self.verifier_node_id,
            "synthesis_node_id": self.synthesis_node_id,
        }


class GraphExecutor:
    """Expose the bounded execution plan for the current workflow."""

    def __init__(self, graph: WorkflowGraph) -> None:
        self._graph = graph

    def build_plan(self) -> ExecutionPlan:
        return ExecutionPlan(
            specialist_roles=self._graph.specialist_roles,
            verifier_node_id=_single_node_id(self._graph, node_type="verifier"),
            synthesis_node_id=_single_node_id(self._graph, node_type="coordinator"),
        )


def _single_node_id(graph: WorkflowGraph, *, node_type: str) -> str | None:
    matching = [node.id for node in graph.nodes if node.type == node_type]
    if len(matching) > 1:
        raise ValueError(f"workflow graph must not define multiple {node_type} nodes")
    return matching[0] if matching else None
