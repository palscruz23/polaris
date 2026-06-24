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
    def __init__(
        self,
        responses: list[AgentModelResponse],
        review_responses: list[str] | None = None,
    ):
        self.responses = responses
        self.review_responses = review_responses or [
            '{"accepted": true, "reason": "Supported.", "revision_guidance": null}'
        ]
        self.exchange_counts: list[int] = []
        self.tool_counts: list[int] = []
        self.review_messages: list[Sequence[ChatMessage]] = []

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
        del max_output_tokens
        self.review_messages.append(messages)
        return self.review_responses.pop(0)

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
            AgentToolDefinition(
                name="plan_reliability_improvement",
                description="Plan reliability improvements.",
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
    assert len(provider.review_messages) == 1


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
    assert provider.tool_counts == [4, 4, 4]


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
        "answer_reviewing",
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
    assert provider.tool_counts == [4, 4, 0]


def test_orchestrator_revises_answer_after_failed_quality_review() -> None:
    provider = ScriptedProvider(
        [
            AgentModelResponse(content="Draft answer missing limitations."),
            AgentModelResponse(content="Revised answer with clear limitations."),
        ],
        review_responses=[
            (
                '{"accepted": false, "reason": "Missing limitations.", '
                '"revision_guidance": "State limitations."}'
            ),
            '{"accepted": true, "reason": "Now supported.", "revision_guidance": null}',
        ],
    )
    registry = RecordingRegistry()
    progress_events: list[OrchestrationProgress] = []
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Give a recommendation.")],
        max_output_tokens=500,
        progress=progress_events.append,
    )

    assert response == "Revised answer with clear limitations."
    assert registry.calls == []
    assert [event.stage for event in progress_events] == [
        "reviewing_request",
        "answer_reviewing",
        "answer_revising",
        "answer_reviewing",
    ]


def test_orchestrator_revision_can_call_additional_specialist() -> None:
    improvement_call = AgentToolCall(
        id="call-improvement",
        name="plan_reliability_improvement",
        arguments={"opportunity_limit": 2},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content="Draft answer without roadmap."),
            AgentModelResponse(content=None, tool_calls=(improvement_call,)),
            AgentModelResponse(content="Revised answer with roadmap evidence."),
        ],
        review_responses=[
            (
                '{"accepted": false, "reason": "Need improvement roadmap.", '
                '"revision_guidance": "Call Reliability Improvement if needed."}'
            ),
            '{"accepted": true, "reason": "Roadmap included.", "revision_guidance": null}',
        ],
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Build an action roadmap.")],
        max_output_tokens=500,
    )

    assert response == "Revised answer with roadmap evidence."
    assert registry.calls == [improvement_call]
    assert provider.exchange_counts == [0, 0, 1]


def test_orchestrator_returns_honest_answer_after_quality_review_limit() -> None:
    provider = ScriptedProvider(
        [
            AgentModelResponse(content="Draft answer."),
            AgentModelResponse(content="Revision 1."),
            AgentModelResponse(content="Revision 2."),
            AgentModelResponse(content="Revision 3."),
        ],
        review_responses=[
            (
                '{"accepted": false, "reason": "Still incomplete.", '
                '"revision_guidance": "Improve evidence."}'
            ),
            (
                '{"accepted": false, "reason": "Still incomplete.", '
                '"revision_guidance": "Improve evidence."}'
            ),
            (
                '{"accepted": false, "reason": "Still incomplete.", '
                '"revision_guidance": "Improve evidence."}'
            ),
            (
                '{"accepted": false, "reason": "Still incomplete.", '
                '"revision_guidance": "Improve evidence."}'
            ),
        ],
    )
    registry = RecordingRegistry()
    progress_events: list[OrchestrationProgress] = []
    orchestrator = ReliabilityAgentOrchestrator(
        provider,
        registry,
        max_quality_review_loops=3,
    )

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Give a complete answer.")],
        max_output_tokens=500,
        progress=progress_events.append,
    )

    assert response.startswith("Revision 3.")
    assert "best supported answer" in response
    assert "Still incomplete." in response
    assert progress_events[-1].stage == "answer_review_limit_reached"
