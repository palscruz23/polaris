import math
from collections.abc import Sequence

from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentModelResponse,
    AgentToolCall,
    AgentToolDefinition,
    AgentToolExchange,
    AgentToolResult,
)
from app.domain.progress import (
    OrchestrationProgress,
    ProgressCallback,
)
from app.providers.base import ChatProvider
from app.services.reliability_agent_orchestrator import (
    ReliabilityAgentOrchestrator,
)


class ScriptedProvider(ChatProvider):
    def __init__(self, responses: list[AgentModelResponse]):
        self.responses = responses
        self.exchange_counts: list[int] = []
        self.tool_counts: list[int] = []

    @property
    def name(self) -> str:
        return "test"

    @property
    def model(self) -> str:
        return "test-model"

    @property
    def context_window(self) -> int:
        return 4_096

    def count_tokens(
        self,
        messages: Sequence[ChatMessage],
    ) -> int:
        return math.ceil(
            sum(len(message.role) + len(message.content) for message in messages)
            / 3
        )

    def generate(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
    ) -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        tools: Sequence[AgentToolDefinition],
        exchanges: Sequence[AgentToolExchange] = (),
    ) -> AgentModelResponse:
        del messages, max_output_tokens
        self.exchange_counts.append(len(exchanges))
        self.tool_counts.append(len(tools))

        return self.responses.pop(0)


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls: list[AgentToolCall] = []
        self.definitions = (
            AgentToolDefinition(
                name="search_equipment_master",
                description="Search equipment master data.",
                input_schema={"type": "object", "properties": {}},
            ),
            AgentToolDefinition(
                name="analyze_defect_elimination",
                description="Analyze reliability failures.",
                input_schema={"type": "object", "properties": {}},
            ),
            AgentToolDefinition(
                name="review_maintenance_strategy",
                description="Review maintenance strategy.",
                input_schema={"type": "object", "properties": {}},
            ),
        )

    def execute(
        self,
        call: AgentToolCall,
        progress: ProgressCallback | None = None,
    ) -> AgentToolResult:
        del progress
        self.calls.append(call)
        return AgentToolResult(
            call_id=call.id,
            tool_name=call.name,
            content=f'{{"completed":"{call.name}"}}',
        )


def test_orchestrator_returns_direct_response_without_specialist_call() -> None:
    provider = ScriptedProvider(
        [AgentModelResponse(content="MTBF means mean time between failures.")]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="What is MTBF?")],
        max_output_tokens=500,
    )

    assert response == "MTBF means mean time between failures."
    assert registry.calls == []
    assert provider.exchange_counts == [0]


def test_orchestrator_executes_dependent_specialists_sequentially() -> None:
    defect_call = AgentToolCall(
        id="call-1",
        name="analyze_defect_elimination",
        arguments={"bad_actor_limit": 3},
    )
    strategy_call = AgentToolCall(
        id="call-2",
        name="review_maintenance_strategy",
        arguments={"equipment_numbers": ["P-101"]},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(defect_call,)),
            AgentModelResponse(content=None, tool_calls=(strategy_call,)),
            AgentModelResponse(content="Prioritize P-101 and revise its PM."),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[
            ChatMessage(
                role="user",
                content="Find bad actors and review their strategies.",
            )
        ],
        max_output_tokens=500,
    )

    assert response == "Prioritize P-101 and revise its PM."
    assert registry.calls == [defect_call, strategy_call]
    assert provider.exchange_counts == [0, 1, 2]
    assert provider.tool_counts == [3, 3, 3]


def test_orchestrator_reports_master_data_progress() -> None:
    equipment_call = AgentToolCall(
        id="call-1",
        name="search_equipment_master",
        arguments={"query": "pump"},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(equipment_call,)),
            AgentModelResponse(content="I found the matching pumps."),
        ]
    )
    registry = RecordingRegistry()
    progress_events: list[OrchestrationProgress] = []
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[
            ChatMessage(
                role="user",
                content="List pumps in the equipment dataset.",
            )
        ],
        max_output_tokens=500,
        progress=progress_events.append,
    )

    assert response == "I found the matching pumps."
    assert progress_events[1] == OrchestrationProgress(
        stage="specialist_started",
        specialist="master_data",
        message=(
            "Reliability Agent is coordinating with the Master Data Agent."
        ),
    )


def test_orchestrator_reports_natural_language_specialist_progress() -> None:
    strategy_call = AgentToolCall(
        id="call-1",
        name="review_maintenance_strategy",
        arguments={"equipment_numbers": ["P-101"]},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(strategy_call,)),
            AgentModelResponse(content="Review complete."),
        ]
    )
    registry = RecordingRegistry()
    progress_events: list[OrchestrationProgress] = []
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[
            ChatMessage(
                role="user",
                content="Review the strategy for P-101.",
            )
        ],
        max_output_tokens=500,
        progress=progress_events.append,
    )

    assert response == "Review complete."
    assert [event.stage for event in progress_events] == [
        "reviewing_request",
        "specialist_started",
        "synthesizing",
    ]
    assert progress_events[1].message == (
        "Reliability Agent is coordinating with the Maintenance Strategy Agent."
    )


def test_orchestrator_reports_duplicate_calls_without_reexecuting() -> None:
    first_call = AgentToolCall(
        id="call-1",
        name="analyze_defect_elimination",
        arguments={"bad_actor_limit": 3},
    )
    duplicate_call = AgentToolCall(
        id="call-2",
        name="analyze_defect_elimination",
        arguments={"bad_actor_limit": 3},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(first_call,)),
            AgentModelResponse(content=None, tool_calls=(duplicate_call,)),
            AgentModelResponse(content="Using the first analysis result."),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Analyze failures.")],
        max_output_tokens=500,
    )

    assert response == "Using the first analysis result."
    assert registry.calls == [first_call]


def test_orchestrator_forces_final_response_at_tool_call_limit() -> None:
    calls = [
        AgentToolCall(
            id=f"call-{index}",
            name="analyze_defect_elimination",
            arguments={"bad_actor_limit": index},
        )
        for index in range(1, 4)
    ]
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(calls[0],)),
            AgentModelResponse(content=None, tool_calls=(calls[1],)),
            AgentModelResponse(content="Final answer after bounded analysis."),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(
        provider,
        registry,
        max_tool_calls=2,
    )

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Keep analyzing.")],
        max_output_tokens=500,
    )

    assert response == "Final answer after bounded analysis."
    assert registry.calls == calls[:2]
    assert provider.tool_counts == [3, 3, 0]
