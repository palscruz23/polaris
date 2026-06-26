import json
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
        self.tool_messages: list[Sequence[ChatMessage]] = []

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
        del max_output_tokens
        self.tool_messages.append(messages)
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
            AgentModelResponse(content="Draft answer."),
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
    assert provider.exchange_counts == [0, 1, 2, 2]
    assert provider.tool_counts == [3, 3, 3, 1]


def test_orchestrator_reports_master_data_progress() -> None:
    equipment_call = AgentToolCall(
        id="call-1",
        name="search_equipment_master",
        arguments={"query": "pump"},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(equipment_call,)),
            AgentModelResponse(content="Draft pump list."),
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
            AgentModelResponse(content="Draft review."),
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
            AgentModelResponse(content="Draft answer."),
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
    assert provider.tool_counts == [3, 3, 1]


def test_orchestrator_final_synthesis_can_sequence_roadmap() -> None:
    defect_call = AgentToolCall(
        id="call-1",
        name="analyze_defect_elimination",
        arguments={"bad_actor_limit": 1},
    )
    roadmap_call = AgentToolCall(
        id="call-roadmap",
        name="roadmap_planner",
        arguments={
            "opportunities": [
                {
                    "equipment_number": "P-101",
                    "priority": "high",
                    "estimated_annual_value": "52000",
                    "value_basis": "Repeat seal leakage with downtime.",
                    "evidence": ["WO-101", "WO-102"],
                },
                {
                    "equipment_number": "P-102",
                    "priority": "medium",
                    "estimated_annual_value": "8000",
                    "value_basis": "Pump bearing failures.",
                    "evidence": ["WO-103"],
                },
                {
                    "equipment_number": "CV-201",
                    "priority": "medium",
                    "estimated_annual_value": "7000",
                    "value_basis": "Recurring belt slippage.",
                    "evidence": ["WO-201"],
                },
            ],
            "action_plans": [
                {
                    "equipment_number": "P-101",
                    "title": "Reliability improvement plan - P-101",
                },
                {
                    "equipment_number": "P-102",
                    "title": "Reliability improvement plan - P-102",
                },
                {
                    "equipment_number": "CV-201",
                    "title": "Reliability improvement plan - CV-201",
                },
            ],
        },
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(defect_call,)),
            AgentModelResponse(content="Draft answer."),
            AgentModelResponse(content=None, tool_calls=(roadmap_call,)),
            AgentModelResponse(content="P-101 belongs in now; CV-201 is next."),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond_with_metadata(
        messages=[ChatMessage(role="user", content="Prioritize the work.")],
        max_output_tokens=500,
    )
    roadmap_exchange = response.tool_calls[-1]

    assert response.content == "P-101 belongs in now; CV-201 is next."
    assert roadmap_exchange.call.name == "roadmap_planner"
    assert '"horizon": "now"' in roadmap_exchange.result.content
    assert '"horizon": "next"' in roadmap_exchange.result.content
    assert provider.tool_counts == [3, 3, 1, 0]
    assert [call.call_type for call in response.internal_calls] == [
        "agent_tool_selection",
        "agent_tool_selection",
        "agent_roadmap_planning",
        "agent_final_synthesis",
        "answer_review",
    ]


def test_orchestrator_final_synthesis_prioritizes_recommendations_by_urgency() -> None:
    strategy_call = AgentToolCall(
        id="call-1",
        name="review_maintenance_strategy",
        arguments={"maximum_assets": 1},
    )
    roadmap_call = AgentToolCall(
        id="call-roadmap",
        name="roadmap_planner",
        arguments={
            "recommendations": [
                {
                    "equipment_number": "CV-201",
                    "suggestion": "Keep the current inspection task.",
                    "urgency": "low",
                    "reason": "Current strategy covers observed demand.",
                },
                {
                    "equipment_number": "P-101",
                    "suggestion": "Add a seal failure control task.",
                    "urgency": "urgent",
                    "reason": "Repeat failures are causing high downtime.",
                    "estimated_annual_value": "45000",
                    "evidence": ["WO-101", "WO-102"],
                },
                {
                    "equipment_number": "P-102",
                    "suggestion": "Modify the bearing inspection interval.",
                    "urgency": "medium",
                    "reason": "Recurrence is close to the task interval.",
                    "estimated_annual_value": "12000",
                },
            ]
        },
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content=None, tool_calls=(strategy_call,)),
            AgentModelResponse(content="Draft recommendation summary."),
            AgentModelResponse(content=None, tool_calls=(roadmap_call,)),
            AgentModelResponse(content="P-101 is the most urgent item."),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond_with_metadata(
        messages=[ChatMessage(role="user", content="Sequence the recommendations.")],
        max_output_tokens=500,
    )
    roadmap = json.loads(response.tool_calls[-1].result.content)

    assert response.content == "P-101 is the most urgent item."
    assert roadmap[0]["equipment_number"] == "P-101"
    assert roadmap[0]["priority"] == "high"
    assert roadmap[0]["horizon"] == "now"
    assert roadmap[2]["equipment_number"] == "CV-201"
    assert roadmap[2]["priority"] == "low"


def test_orchestrator_final_synthesis_includes_investigation_decision_matrix() -> None:
    defect_call = AgentToolCall(
        id="call-1",
        name="analyze_defect_elimination",
        arguments={"equipment_numbers": ["P-101"]},
    )
    strategy_call = AgentToolCall(
        id="call-2",
        name="review_maintenance_strategy",
        arguments={"equipment_numbers": ["P-101"]},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(
                content=None,
                tool_calls=(defect_call, strategy_call),
            ),
            AgentModelResponse(content="Draft combined recommendation."),
            AgentModelResponse(
                content=(
                    "P-101 is critical, so run an investigation before "
                    "strategy changes."
                ),
            ),
        ]
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond_with_metadata(
        messages=[
            ChatMessage(
                role="user",
                content="Review recommendations for P-101.",
            )
        ],
        max_output_tokens=500,
    )
    final_synthesis_messages = provider.tool_messages[2]

    assert "run an investigation" in response.content
    assert any(
        "High or critical equipment criticality" in message.content
        and "Medium equipment criticality" in message.content
        and "Low equipment criticality" in message.content
        for message in final_synthesis_messages
    )


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
    strategy_call = AgentToolCall(
        id="call-strategy",
        name="review_maintenance_strategy",
        arguments={"maximum_assets": 1},
    )
    provider = ScriptedProvider(
        [
            AgentModelResponse(content="Draft answer without strategy evidence."),
            AgentModelResponse(content=None, tool_calls=(strategy_call,)),
            AgentModelResponse(content="Revised answer with strategy evidence."),
        ],
        review_responses=[
            (
                '{"accepted": false, "reason": "Need strategy evidence.", '
                '"revision_guidance": "Call Maintenance Strategy if needed."}'
            ),
            '{"accepted": true, "reason": "Strategy included.", "revision_guidance": null}',
        ],
    )
    registry = RecordingRegistry()
    orchestrator = ReliabilityAgentOrchestrator(provider, registry)

    response = orchestrator.respond(
        messages=[ChatMessage(role="user", content="Review maintenance strategy.")],
        max_output_tokens=500,
    )

    assert response == "Revised answer with strategy evidence."
    assert registry.calls == [strategy_call]
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
