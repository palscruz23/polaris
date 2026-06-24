import json
from collections.abc import Sequence
from time import perf_counter

from app.agents.registry import SpecialistRegistry
from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentAnswerReview,
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
                observer=model_call_observer,
            )

            if not response.tool_calls:
                if response.content:
                    return self._review_and_revise(
                        messages=messages,
                        max_output_tokens=max_output_tokens,
                        exchanges=exchanges,
                        draft=response.content,
                        seen_calls=seen_calls,
                        tool_call_count=tool_call_count,
                        progress=progress,
                        model_call_observer=model_call_observer,
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
        final_response = self._generate_with_tools(
            call_type="agent_final_synthesis",
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=(),
            exchanges=exchanges,
            observer=model_call_observer,
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
                model_call_observer=model_call_observer,
            )

        raise ChatServiceError(
            "The Reliability Agent could not produce a final response."
        )

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
            "plan_reliability_improvement": "reliability_improvement",
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
            "plan_reliability_improvement": (
                "Reliability Agent is coordinating with the Reliability "
                "Improvement Agent."
            ),
        }.get(
            tool_name,
            "Reliability Agent is coordinating specialist analysis.",
        )
