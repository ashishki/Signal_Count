"""Serializable workflow graph state for job metadata."""

from __future__ import annotations

from dataclasses import dataclass

from app.orchestration.graph import WorkflowGraph


@dataclass(frozen=True)
class GraphNodeState:
    id: str
    type: str
    status: str
    optional: bool = False


@dataclass(frozen=True)
class GraphState:
    nodes: tuple[GraphNodeState, ...]
    edges: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "status": node.status,
                    "optional": node.optional,
                }
                for node in self.nodes
            ],
            "edges": [list(edge) for edge in self.edges],
        }


def build_graph_state(
    *,
    graph: WorkflowGraph,
    completed_roles: list[str],
    missing_roles: list[str],
    rejected_roles: list[str],
    verifier_ran: bool,
    synthesis_ran: bool,
) -> GraphState:
    completed = set(completed_roles)
    missing = set(missing_roles)
    rejected = set(rejected_roles)

    nodes: list[GraphNodeState] = []
    for node in graph.nodes:
        if node.type == "specialist":
            status = _specialist_status(
                role=node.id,
                completed=completed,
                missing=missing,
                rejected=rejected,
            )
        elif node.type == "verifier":
            status = "completed" if verifier_ran else "skipped"
        else:
            status = "completed" if synthesis_ran else "pending"
        nodes.append(
            GraphNodeState(
                id=node.id,
                type=node.type,
                status=status,
                optional=node.optional,
            )
        )

    return GraphState(nodes=tuple(nodes), edges=graph.edges)


def _specialist_status(
    *,
    role: str,
    completed: set[str],
    missing: set[str],
    rejected: set[str],
) -> str:
    if role in rejected:
        return "rejected"
    if role in missing:
        return "missing"
    if role in completed:
        return "completed"
    return "pending"
