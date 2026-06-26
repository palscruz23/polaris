import json
from collections.abc import Sequence
from dataclasses import asdict
from decimal import Decimal
from time import perf_counter
from typing import Any

from app.agents.registry import SpecialistRegistry
from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentAnswerReview,
    AgentInternalCall,
    AgentModelCallTrace,
    AgentModelResponse,
    AgentOrchestrationResponse,
    AgentToolCall,
    AgentToolDefinition,
    AgentToolExchange,
    AgentToolResult,
    ModelCallObserver,
)
from app.domain.progress import ProgressCallback, report_progress
from app.exceptions import ChatServiceError
from app.providers.base import ChatProvider
from app.tools.reliability_improvement import (
    ReliabilityImprovementActionPlan,
    ReliabilityImprovementOpportunity,
    RoadmapPlannerTool,
)

INTERNAL_CALL_MESSAGES: dict[str, str] = {
    "agent_tool_selection": "Analyze request and select specialist",
    "agent_final_synthesis": "Consolidate findings into final response",
    "answer_review": "Quality gate — verify answer against evidence",
    "answer_revision": "Revise answer to meet quality standards",
    "answer_revision_final": "Finalize revised answer",
}

RECOMMENDATION_DECISION_MATRIX = """
When consolidating Defect Elimination and Maintenance Strategy recommendations,
make an explicit decision between investigation and strategy improvement when
the evidence supports both options:
- High or critical equipment criticality: prefer a formal defect-elimination
  investigation before or alongside strategy changes.
- Medium equipment criticality: first assess whether the maintenance strategy
  recommendation is likely sufficient to prevent recurrence. If coverage,
  frequency, or condition-monitoring improvements appear sufficient, recommend
  strategy improvement with verification. If repeat failures, high downtime,
  unclear cause, or weak strategy evidence remain, recommend investigation.
- Low equipment criticality: prefer maintenance strategy improvement and
  monitoring unless the evidence shows exceptional risk, cost, downtime, or
  safety concern.
Always explain the decision using available evidence such as criticality,
repeat-failure pattern, bad-actor ranking, strategy coverage, frequency risk,
downtime, and cost. Do not claim strategy improvement is sufficient when the
specialist evidence does not support that conclusion.
""".strip()

ROADMAP_PLANNER_TOOL_DEFINITION = AgentToolDefinition(
    name="roadmap_planner",
    description=(
        "Sequence candidate reliability improvement opportunities into now, "
        "next, and later roadmap horizons during final synthesis. Use this "
        "only after specialist evidence has identified opportunities or "
        "recommended actions that need ordering. When sequencing "
        "recommendations, set priority from the urgency of the issue."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "equipment_number": {"type": "string"},
                        "title": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "suggestion": {"type": "string"},
                        "reason": {"type": "string"},
                        "urgency": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "estimated_annual_value": {
                            "type": ["number", "string"]
                        },
                        "value_basis": {"type": "string"},
                        "failure_mode": {"type": ["string", "null"]},
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["equipment_number"],
                },
            },
            "opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "equipment_number": {"type": "string"},
                        "equipment_description": {
                            "type": ["string", "null"]
                        },
                        "equipment_type": {"type": ["string", "null"]},
                        "criticality": {"type": ["string", "null"]},
                        "opportunity_type": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "estimated_annual_value": {
                            "type": ["number", "string"]
                        },
                        "value_basis": {"type": "string"},
                        "evidence": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "equipment_number",
                        "priority",
                        "estimated_annual_value",
                        "value_basis",
                    ],
                },
            },
            "action_plans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "equipment_number": {"type": "string"},
                        "title": {"type": "string"},
                        "owner_role": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "actions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "milestones": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "deliverables": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["equipment_number", "title"],
                },
            },
        },
        "anyOf": [
            {"required": ["recommendations"]},
            {"required": ["opportunities"]},
        ],
    },
)


class ReliabilityAgentOrchestrator:
    def __init__(
        self,
        provider: ChatProvider,
        registry: SpecialistRegistry,
        max_tool_calls: int = 5,
        max_quality_review_loops: int = 3,
    ):
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1.")
        if max_quality_review_loops < 0:
            raise ValueError("max_quality_review_loops cannot be negative.")

        self.provider = provider
        self.registry = registry
        self.max_tool_calls = max_tool_calls
        self.max_quality_review_loops = max_quality_review_loops

    def respond(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        progress: ProgressCallback | None = None,
        model_call_observer: ModelCallObserver | None = None,
    ) -> str:
        return self.respond_with_metadata(
            messages=messages,
            max_output_tokens=max_output_tokens,
            progress=progress,
            model_call_observer=model_call_observer,
        ).content

    def respond_with_metadata(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        progress: ProgressCallback | None = None,
        model_call_observer: ModelCallObserver | None = None,
    ) -> AgentOrchestrationResponse:
        exchanges: list[AgentToolExchange] = []
        seen_calls: set[str] = set()
        tool_call_count = 0
        internal_calls: list[AgentInternalCall] = []

        def _collect(trace: AgentModelCallTrace) -> None:
            internal_calls.append(
                AgentInternalCall(
                    call_type=trace.call_type,
                    message=INTERNAL_CALL_MESSAGES.get(
                        trace.call_type, trace.call_type
                    ),
                )
            )
            if model_call_observer is not None:
                model_call_observer(trace)

        observer = _collect

        report_progress(
            progress,
            stage="reviewing_request",
            message="Reliability Agent is reviewing your request.",
        )

        while tool_call_count < self.max_tool_calls:
            response = self._generate_with_tools(
                call_type="agent_tool_selection",
                messages=messages,
                max_output_tokens=max_output_tokens,
                tools=self.registry.definitions,
                exchanges=exchanges,
                observer=observer,
            )

            if not response.tool_calls:
                if response.content:
                    if exchanges:
                        final_response = self._final_synthesis(
                            messages=messages,
                            max_output_tokens=max_output_tokens,
                            exchanges=exchanges,
                            progress=progress,
                            observer=observer,
                        )
                        if not final_response.content:
                            raise ChatServiceError(
                                "The Reliability Agent could not produce a "
                                "final response."
                            )
                        response = final_response

                    return self._review_and_revise(
                        messages=messages,
                        max_output_tokens=max_output_tokens,
                        exchanges=exchanges,
                        draft=response.content,
                        seen_calls=seen_calls,
                        tool_call_count=tool_call_count,
                        progress=progress,
                        model_call_observer=observer,
                        internal_calls=internal_calls,
                    )

                raise ChatServiceError(
                    "The Reliability Agent returned an empty response."
                )

            for call in response.tool_calls:
                if tool_call_count >= self.max_tool_calls:
                    break

                report_progress(
                    progress,
                    stage="specialist_started",
                    specialist=self._specialist_name(call.name),
                    message=self._coordination_message(call.name),
                )
                result = self._execute(call, seen_calls, progress)
                exchanges.append(
                    AgentToolExchange(
                        call=call,
                        result=result,
                    )
                )
                tool_call_count += 1

        report_progress(
            progress,
            stage="synthesizing",
            message="Reliability Agent is consolidating the findings.",
        )
        final_response = self._final_synthesis(
            messages=messages,
            max_output_tokens=max_output_tokens,
            exchanges=exchanges,
            progress=progress,
            observer=observer,
        )

        if final_response.content:
            return self._review_and_revise(
                messages=messages,
                max_output_tokens=max_output_tokens,
                exchanges=exchanges,
                draft=final_response.content,
                seen_calls=seen_calls,
                tool_call_count=tool_call_count,
                progress=progress,
                model_call_observer=observer,
                internal_calls=internal_calls,
            )

        raise ChatServiceError(
            "The Reliability Agent could not produce a final response."
        )

    def _final_synthesis(
        self,
        *,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        exchanges: list[AgentToolExchange],
        progress: ProgressCallback | None,
        observer: ModelCallObserver | None,
    ) -> AgentModelResponse:
        synthesis_messages = self._with_recommendation_decision_matrix(messages)
        response = self._generate_with_tools(
            call_type="agent_final_synthesis",
            messages=synthesis_messages,
            max_output_tokens=max_output_tokens,
            tools=(ROADMAP_PLANNER_TOOL_DEFINITION,),
            exchanges=exchanges,
            observer=observer,
        )

        if response.tool_calls:
            for call in response.tool_calls:
                report_progress(
                    progress,
                    stage="tool_started",
                    specialist="reliability_agent",
                    tool=call.name,
                    message=(
                        "Reliability Agent is sequencing opportunities into "
                        "a roadmap."
                    ),
                )
                exchanges.append(
                    AgentToolExchange(
                        call=call,
                        result=self._execute_final_synthesis_tool(call),
                    )
                )

            response = self._generate_with_tools(
                call_type="agent_final_synthesis",
                messages=synthesis_messages,
                max_output_tokens=max_output_tokens,
                tools=(),
                exchanges=exchanges,
                observer=observer,
            )

        return response

    def _execute(
        self,
        call: AgentToolCall,
        seen_calls: set[str],
        progress: ProgressCallback | None,
    ) -> AgentToolResult:
        signature = json.dumps(
            {
                "name": call.name,
                "arguments": call.arguments,
            },
            sort_keys=True,
            default=str,
        )

        if signature in seen_calls:
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=(
                    "This specialist call was already executed with the same "
                    "arguments. Use the existing result or choose a different "
                    "capability."
                ),
                is_error=True,
            )

        seen_calls.add(signature)
        return self.registry.execute(call, progress)

    def _execute_final_synthesis_tool(
        self,
        call: AgentToolCall,
    ) -> AgentToolResult:
        if call.name != ROADMAP_PLANNER_TOOL_DEFINITION.name:
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=f"Unknown final synthesis tool: {call.name}.",
                is_error=True,
            )

        try:
            recommendation_payloads = self._list_argument(
                call.arguments,
                "recommendations",
            )
            recommendation_opportunities = [
                self._opportunity_from_recommendation_payload(payload)
                for payload in recommendation_payloads
            ]
            recommendation_action_plans = [
                self._action_plan_from_recommendation_payload(payload)
                for payload in recommendation_payloads
            ]
            opportunities = recommendation_opportunities + [
                self._opportunity_from_payload(payload)
                for payload in self._list_argument(
                    call.arguments,
                    "opportunities",
                )
            ]
            opportunities = sorted(
                opportunities,
                key=lambda item: (
                    _priority_score(item.priority),
                    item.estimated_annual_value,
                ),
                reverse=True,
            )
            action_plans = recommendation_action_plans + [
                self._action_plan_from_payload(payload)
                for payload in self._list_argument(
                    call.arguments,
                    "action_plans",
                )
            ]
            roadmap = RoadmapPlannerTool().run(opportunities, action_plans)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            return AgentToolResult(
                call_id=call.id,
                tool_name=call.name,
                content=(
                    "RoadmapPlannerTool could not sequence the supplied "
                    f"opportunities: {error}."
                ),
                is_error=True,
            )

        return AgentToolResult(
            call_id=call.id,
            tool_name=call.name,
            content=json.dumps(
                [asdict(item) for item in roadmap],
                default=str,
            ),
        )

    @staticmethod
    def _list_argument(
        arguments: dict[str, Any],
        key: str,
    ) -> list[dict[str, Any]]:
        value = arguments.get(key, [])
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError(f"{key} must be a list.")
        if not all(isinstance(item, dict) for item in value):
            raise TypeError(f"{key} must contain objects.")
        return value

    @staticmethod
    def _opportunity_from_payload(
        payload: dict[str, Any],
    ) -> ReliabilityImprovementOpportunity:
        return ReliabilityImprovementOpportunity(
            equipment_number=str(payload["equipment_number"]),
            equipment_description=_optional_string(
                payload.get("equipment_description")
            ),
            equipment_type=_optional_string(payload.get("equipment_type")),
            criticality=_optional_string(payload.get("criticality")),
            opportunity_type=str(
                payload.get("opportunity_type")
                or "reliability_improvement"
            ),
            priority=_priority(payload.get("priority")),
            estimated_annual_value=Decimal(
                str(payload["estimated_annual_value"])
            ),
            value_basis=str(payload["value_basis"]),
            evidence=_string_list(payload.get("evidence")),
        )

    @staticmethod
    def _opportunity_from_recommendation_payload(
        payload: dict[str, Any],
    ) -> ReliabilityImprovementOpportunity:
        recommendation = _recommendation_text(payload)
        priority = _priority(payload.get("priority") or payload.get("urgency"))
        value_basis = str(
            payload.get("value_basis")
            or payload.get("reason")
            or recommendation
        )
        failure_mode = _optional_string(payload.get("failure_mode"))
        opportunity_type = (
            f"recommendation:{failure_mode}"
            if failure_mode
            else "recommendation"
        )

        return ReliabilityImprovementOpportunity(
            equipment_number=str(payload["equipment_number"]),
            equipment_description=None,
            equipment_type=None,
            criticality=None,
            opportunity_type=opportunity_type,
            priority=priority,
            estimated_annual_value=Decimal(
                str(payload.get("estimated_annual_value") or "0")
            ),
            value_basis=value_basis,
            evidence=_string_list(payload.get("evidence")),
        )

    @staticmethod
    def _action_plan_from_payload(
        payload: dict[str, Any],
    ) -> ReliabilityImprovementActionPlan:
        priority = _priority(payload.get("priority"))
        return ReliabilityImprovementActionPlan(
            equipment_number=str(payload["equipment_number"]),
            title=str(payload["title"]),
            owner_role=str(payload.get("owner_role") or "Reliability Engineer"),
            priority=priority,
            actions=_string_list(payload.get("actions")),
            milestones=_string_list(payload.get("milestones")),
            deliverables=_string_list(payload.get("deliverables")),
        )

    @staticmethod
    def _action_plan_from_recommendation_payload(
        payload: dict[str, Any],
    ) -> ReliabilityImprovementActionPlan:
        recommendation = _recommendation_text(payload)
        return ReliabilityImprovementActionPlan(
            equipment_number=str(payload["equipment_number"]),
            title=str(payload.get("title") or recommendation),
            owner_role="Reliability Engineer",
            priority=_priority(payload.get("priority") or payload.get("urgency")),
            actions=[recommendation],
            milestones=[
                "Confirm urgency and supporting evidence.",
                "Assign owner and implementation window.",
                "Verify the recommendation reduced the issue urgency.",
            ],
            deliverables=[
                "Prioritized recommendation with owner and due date.",
                "Post-action verification against the original issue.",
            ],
        )

    def _review_and_revise(
        self,
        *,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        exchanges: list[AgentToolExchange],
        draft: str,
        seen_calls: set[str],
        tool_call_count: int,
        progress: ProgressCallback | None,
        model_call_observer: ModelCallObserver | None,
        internal_calls: list[AgentInternalCall],
    ) -> AgentOrchestrationResponse:
        if exchanges:
            report_progress(
                progress,
                stage="synthesizing",
                message="Reliability Agent is consolidating the findings.",
            )

        current_answer = draft

        for loop_index in range(self.max_quality_review_loops + 1):
            review = self._review_answer(
                messages=messages,
                answer=current_answer,
                exchanges=exchanges,
                progress=progress,
                model_call_observer=model_call_observer,
            )

            if review.accepted:
                return AgentOrchestrationResponse(
                    content=current_answer,
                    tool_calls=tuple(exchanges),
                    internal_calls=tuple(internal_calls),
                )

            if loop_index >= self.max_quality_review_loops:
                report_progress(
                    progress,
                    stage="answer_review_limit_reached",
                    message=(
                        "Reliability Agent reached the answer review limit "
                        "and is returning the best supported answer with "
                        "limitations."
                    ),
                )
                return AgentOrchestrationResponse(
                    content=self._honest_fallback_answer(
                        current_answer,
                        review,
                    ),
                    tool_calls=tuple(exchanges),
                    internal_calls=tuple(internal_calls),
                )

            report_progress(
                progress,
                stage="answer_revising",
                message=(
                    "Reliability Agent is revising the answer after quality "
                    "review."
                ),
            )
            current_answer, tool_call_count = self._revise_answer(
                messages=messages,
                max_output_tokens=max_output_tokens,
                exchanges=exchanges,
                current_answer=current_answer,
                review=review,
                seen_calls=seen_calls,
                tool_call_count=tool_call_count,
                progress=progress,
                model_call_observer=model_call_observer,
            )

        return AgentOrchestrationResponse(
            content=current_answer,
            tool_calls=tuple(exchanges),
            internal_calls=tuple(internal_calls),
        )

    def _review_answer(
        self,
        *,
        messages: Sequence[ChatMessage],
        answer: str,
        exchanges: Sequence[AgentToolExchange],
        progress: ProgressCallback | None,
        model_call_observer: ModelCallObserver | None,
    ) -> AgentAnswerReview:
        report_progress(
            progress,
            stage="answer_reviewing",
            message="Reliability Agent is checking answer quality.",
        )
        review_messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are reviewing a reliability-engineering assistant "
                    "answer before it is shown to the user. Return only JSON "
                    "with keys: accepted (boolean), reason (string), and "
                    "revision_guidance (string or null). Accept only when the "
                    "answer directly addresses the user request, is supported "
                    "by available specialist evidence, does not overstate "
                    "certainty, and states important limitations."
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    "Original conversation messages:\n"
                    f"{self._messages_summary(messages)}\n\n"
                    "Specialist evidence:\n"
                    f"{self._exchanges_summary(exchanges)}\n\n"
                    "Draft answer:\n"
                    f"{answer}"
                ),
            ),
        ]

        try:
            content = self._generate(
                call_type="answer_review",
                messages=review_messages,
                max_output_tokens=800,
                observer=model_call_observer,
            )
            payload = json.loads(content)
        except (ChatServiceError, json.JSONDecodeError, TypeError, ValueError):
            return AgentAnswerReview(
                accepted=True,
                reason=(
                    "Answer review was unavailable, so the draft answer is "
                    "being used."
                ),
            )

        return AgentAnswerReview(
            accepted=bool(payload.get("accepted")),
            reason=str(payload.get("reason") or "No review reason provided."),
            revision_guidance=(
                str(payload["revision_guidance"])
                if payload.get("revision_guidance") is not None
                else None
            ),
        )

    def _revise_answer(
        self,
        *,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        exchanges: list[AgentToolExchange],
        current_answer: str,
        review: AgentAnswerReview,
        seen_calls: set[str],
        tool_call_count: int,
        progress: ProgressCallback | None,
        model_call_observer: ModelCallObserver | None,
    ) -> tuple[str, int]:
        revision_messages = [
            *messages,
            ChatMessage(role="assistant", content=current_answer),
            ChatMessage(
                role="user",
                content=(
                    "Revise the answer using the quality review below. You may "
                    "call another registered specialist only if additional "
                    "stored reliability evidence is needed. If the evidence is "
                    "still incomplete, provide the most honest supported answer "
                    "and clearly state limitations.\n\n"
                    f"Review reason: {review.reason}\n"
                    f"Revision guidance: {review.revision_guidance or 'None'}"
                ),
            ),
        ]
        revision_messages = self._with_recommendation_decision_matrix(
            revision_messages
        )

        while tool_call_count < self.max_tool_calls:
            response = self._generate_with_tools(
                call_type="answer_revision",
                messages=revision_messages,
                max_output_tokens=max_output_tokens,
                tools=self.registry.definitions,
                exchanges=exchanges,
                observer=model_call_observer,
            )

            if not response.tool_calls:
                if response.content:
                    return response.content, tool_call_count

                raise ChatServiceError(
                    "The Reliability Agent returned an empty revision."
                )

            for call in response.tool_calls:
                if tool_call_count >= self.max_tool_calls:
                    break

                report_progress(
                    progress,
                    stage="specialist_started",
                    specialist=self._specialist_name(call.name),
                    message=self._coordination_message(call.name),
                )
                result = self._execute(call, seen_calls, progress)
                exchanges.append(
                    AgentToolExchange(
                        call=call,
                        result=result,
                    )
                )
                tool_call_count += 1

        final_response = self._generate_with_tools(
            call_type="answer_revision_final",
            messages=revision_messages,
            max_output_tokens=max_output_tokens,
            tools=(),
            exchanges=exchanges,
            observer=model_call_observer,
        )

        if final_response.content:
            return final_response.content, tool_call_count

        raise ChatServiceError(
            "The Reliability Agent could not produce a revised response."
        )

    def _generate(
        self,
        *,
        call_type: str,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        observer: ModelCallObserver | None,
    ) -> str:
        start = perf_counter()
        input_tokens = self.provider.count_tokens(messages)

        try:
            content = self.provider.generate(
                messages=messages,
                max_output_tokens=max_output_tokens,
            )
        except Exception as error:
            self._observe_model_call(
                observer,
                AgentModelCallTrace(
                    call_type=call_type,
                    status="failed",
                    latency_ms=self._elapsed_ms(start),
                    input_tokens_estimate=input_tokens,
                    output_tokens_estimate=None,
                    max_output_tokens=max_output_tokens,
                    requested_tool_count=0,
                    error_type=type(error).__name__,
                    error_message=str(error),
                ),
            )
            raise

        self._observe_model_call(
            observer,
            AgentModelCallTrace(
                call_type=call_type,
                status="completed",
                latency_ms=self._elapsed_ms(start),
                input_tokens_estimate=input_tokens,
                output_tokens_estimate=self.provider.count_tokens(
                    [ChatMessage(role="assistant", content=content)]
                ),
                max_output_tokens=max_output_tokens,
                requested_tool_count=0,
                response_tool_call_count=0,
            ),
        )
        return content

    def _generate_with_tools(
        self,
        *,
        call_type: str,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        tools: Sequence[AgentToolDefinition],
        exchanges: Sequence[AgentToolExchange],
        observer: ModelCallObserver | None,
    ) -> AgentModelResponse:
        start = perf_counter()
        input_tokens = self.provider.count_tokens(messages)

        try:
            response = self.provider.generate_with_tools(
                messages=messages,
                max_output_tokens=max_output_tokens,
                tools=tools,
                exchanges=exchanges,
            )
        except Exception as error:
            self._observe_model_call(
                observer,
                AgentModelCallTrace(
                    call_type=call_type,
                    status="failed",
                    latency_ms=self._elapsed_ms(start),
                    input_tokens_estimate=input_tokens,
                    output_tokens_estimate=None,
                    max_output_tokens=max_output_tokens,
                    requested_tool_count=len(tools),
                    error_type=type(error).__name__,
                    error_message=str(error),
                ),
            )
            raise

        output_tokens = (
            self.provider.count_tokens(
                [ChatMessage(role="assistant", content=response.content)]
            )
            if response.content
            else None
        )
        self._observe_model_call(
            observer,
            AgentModelCallTrace(
                call_type=call_type,
                status="completed",
                latency_ms=self._elapsed_ms(start),
                input_tokens_estimate=input_tokens,
                output_tokens_estimate=output_tokens,
                max_output_tokens=max_output_tokens,
                requested_tool_count=len(tools),
                response_tool_call_count=len(response.tool_calls),
            ),
        )
        return response

    @staticmethod
    def _observe_model_call(
        observer: ModelCallObserver | None,
        trace: AgentModelCallTrace,
    ) -> None:
        if observer is not None:
            observer(trace)

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return max(0, round((perf_counter() - start) * 1000))

    @staticmethod
    def _honest_fallback_answer(
        answer: str,
        review: AgentAnswerReview,
    ) -> str:
        return (
            f"{answer}\n\n"
            "Limitations: The answer quality review still found unresolved "
            f"issues after the bounded revision loop: {review.reason}. Treat "
            "this as the best supported answer from the available evidence, "
            "not a fully validated engineering conclusion."
        )

    @staticmethod
    def _messages_summary(messages: Sequence[ChatMessage]) -> str:
        return "\n".join(
            f"{message.role}: {message.content}"
            for message in messages[-8:]
        )

    @staticmethod
    def _with_recommendation_decision_matrix(
        messages: Sequence[ChatMessage],
    ) -> list[ChatMessage]:
        return [
            *messages,
            ChatMessage(
                role="system",
                content=RECOMMENDATION_DECISION_MATRIX,
            ),
        ]

    @staticmethod
    def _exchanges_summary(exchanges: Sequence[AgentToolExchange]) -> str:
        if not exchanges:
            return "No specialist evidence was used."

        return "\n".join(
            (
                f"{exchange.call.name}({exchange.call.arguments}) -> "
                f"{exchange.result.content}"
            )
            for exchange in exchanges
        )

    @staticmethod
    def _specialist_name(tool_name: str) -> str | None:
        return {
            "search_equipment_master": "master_data",
            "analyze_defect_elimination": "defect_elimination",
            "review_maintenance_strategy": "maintenance_strategy",
        }.get(tool_name)

    @staticmethod
    def _coordination_message(tool_name: str) -> str:
        return {
            "search_equipment_master": (
                "Reliability Agent is coordinating with the Master Data Agent."
            ),
            "analyze_defect_elimination": (
                "Reliability Agent is coordinating with the Defect "
                "Elimination Agent."
            ),
            "review_maintenance_strategy": (
                "Reliability Agent is coordinating with the Maintenance "
                "Strategy Agent."
            ),
        }.get(
            tool_name,
            "Reliability Agent is coordinating specialist analysis.",
        )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)


def _priority(value: Any) -> str:
    priority = str(value or "medium").lower().replace(" ", "_")
    priority = {
        "critical": "high",
        "immediate": "high",
        "urgent": "high",
        "asap": "high",
        "soon": "medium",
        "normal": "medium",
        "next": "medium",
        "deferred": "low",
        "later": "low",
    }.get(priority, priority)
    if priority not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported priority: {priority}.")

    return priority


def _priority_score(priority: str) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
    }[priority]


def _recommendation_text(payload: dict[str, Any]) -> str:
    for key in ("recommendation", "suggestion", "title", "reason"):
        value = payload.get(key)
        if value:
            return str(value)

    return f"Prioritize recommendation for {payload['equipment_number']}."


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError("Expected a list of strings.")

    return [str(item) for item in value]
