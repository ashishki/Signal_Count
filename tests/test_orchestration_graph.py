import asyncio

import pytest

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.coordinator.service import CoordinatorService
from app.orchestration.executor import GraphExecutor
from app.orchestration.graph import (
    DEFAULT_WORKFLOW_GRAPH,
    GraphNode,
    WorkflowGraph,
)
from app.schemas.contracts import ScenarioView, SpecialistResponse, ThesisRequest


class StubAXLClient:
    def __init__(self, *, fail_role: str | None = None) -> None:
        self.fail_role = fail_role
        self.dispatch_roles: list[str] = []

    async def fetch_topology(self) -> dict[str, object]:
        return {"local_peer_id": "peer-coordinator-test", "peers": []}

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, object],
    ) -> SpecialistResponse:
        role = str(payload["role"])
        self.dispatch_roles.append(role)
        if role == self.fail_role:
            raise TimeoutError(f"{role} timed out")
        return SpecialistResponse(
            job_id=str(payload["job_id"]),
            node_role=role,
            peer_id=peer_id,
            summary=f"{role} summary",
            scenario_view=ScenarioView(bull=0.3, base=0.4, bear=0.3),
            signals=[service_name],
            risks=[],
            confidence=0.6,
            citations=[],
            timestamp="2026-04-27T00:00:00Z",
        )


class StubMarketDataProvider:
    async def fetch_snapshot(self, request: ThesisRequest) -> dict[str, float]:
        return {"price_return": 0.08, "volatility": 0.18}


class StubNewsFeedProvider:
    async def fetch_headlines(self, request: ThesisRequest) -> list[str]:
        return ["ETF flow expectations improve"]


def test_default_graph_matches_existing_roles() -> None:
    axl_client = StubAXLClient()
    service = _service(axl_client=axl_client)

    result = asyncio.run(
        service.dispatch(job_id="job-graph-default", request=_request())
    )

    assert DEFAULT_WORKFLOW_GRAPH.specialist_roles == ("regime", "narrative", "risk")
    assert axl_client.dispatch_roles == ["regime", "narrative", "risk"]
    assert [response.node_role for response in result.responses] == [
        "regime",
        "narrative",
        "risk",
    ]
    assert result.run_metadata["workflow_graph"] == DEFAULT_WORKFLOW_GRAPH.to_dict()
    assert result.run_metadata["execution_plan"] == {
        "specialist_roles": ["regime", "narrative", "risk"],
        "verifier_node_id": "verifier",
        "synthesis_node_id": "synthesis",
    }
    assert [node["id"] for node in result.run_metadata["graph_state"]["nodes"]] == [
        "regime",
        "narrative",
        "risk",
        "verifier",
        "synthesis",
    ]
    graph_nodes = {
        node["id"]: node for node in result.run_metadata["graph_state"]["nodes"]
    }
    assert graph_nodes["verifier"]["status"] == "skipped"
    assert graph_nodes["synthesis"]["status"] == "completed"


def test_graph_executor_exposes_verifier_and_synthesis_stages() -> None:
    plan = GraphExecutor(DEFAULT_WORKFLOW_GRAPH).build_plan()

    assert plan.specialist_roles == ("regime", "narrative", "risk")
    assert plan.verifier_node_id == "verifier"
    assert plan.synthesis_node_id == "synthesis"


def test_optional_node_failure_is_partial() -> None:
    graph = WorkflowGraph(
        nodes=(
            GraphNode(id="regime", type="specialist"),
            GraphNode(id="narrative", type="specialist"),
            GraphNode(id="risk", type="specialist", optional=True),
            GraphNode(id="verifier", type="verifier"),
            GraphNode(id="synthesis", type="coordinator"),
        ),
        edges=DEFAULT_WORKFLOW_GRAPH.edges,
    )
    service = _service(
        axl_client=StubAXLClient(fail_role="risk"),
        workflow_graph=graph,
    )

    result = asyncio.run(
        service.dispatch(job_id="job-graph-partial", request=_request())
    )

    assert result.partial is True
    assert result.missing_roles == ["risk"]
    graph_nodes = {
        node["id"]: node for node in result.run_metadata["graph_state"]["nodes"]
    }
    assert graph_nodes["risk"] == {
        "id": "risk",
        "type": "specialist",
        "status": "missing",
        "optional": True,
    }
    assert graph_nodes["regime"]["status"] == "completed"
    assert graph_nodes["narrative"]["status"] == "completed"


def test_workflow_graph_rejects_cycles() -> None:
    with pytest.raises(ValueError, match="acyclic"):
        WorkflowGraph(
            nodes=(
                GraphNode(id="a", type="specialist"),
                GraphNode(id="b", type="verifier"),
            ),
            edges=(("a", "b"), ("b", "a")),
        )


def test_graph_executor_rejects_multiple_verifier_nodes() -> None:
    graph = WorkflowGraph(
        nodes=(
            GraphNode(id="regime", type="specialist"),
            GraphNode(id="verifier-a", type="verifier"),
            GraphNode(id="verifier-b", type="verifier"),
        ),
        edges=(("regime", "verifier-a"), ("regime", "verifier-b")),
    )

    with pytest.raises(ValueError, match="multiple verifier"):
        GraphExecutor(graph).build_plan()


def _service(
    *,
    axl_client: StubAXLClient,
    workflow_graph: WorkflowGraph = DEFAULT_WORKFLOW_GRAPH,
) -> CoordinatorService:
    return CoordinatorService(
        axl_client=axl_client,
        registry=AXLRegistry(Settings()),
        market_data_provider=StubMarketDataProvider(),
        news_feed_provider=StubNewsFeedProvider(),
        llm_client=object(),
        workflow_graph=workflow_graph,
    )


def _request() -> ThesisRequest:
    return ThesisRequest(
        thesis="ETH can extend higher on ETF demand.",
        asset="ETH",
        horizon_days=30,
    )
