import json
from collections.abc import Sequence

from app.agents.registry import SpecialistRegistry
from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentToolCall,
    AgentToolExchange,
    AgentToolResult,
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
    ):
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1.")

        self.provider = provider
        self.registry = registry
        self.max_tool_calls = max_tool_calls

    def respond(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        progress: ProgressCallback | None = None,
    ) -> str:
        exchanges: list[AgentToolExchange] = []
        seen_calls: set[str] = set()
        tool_call_count = 0

        report_progress(
            progress,
            stage="reviewing_request",
            message="Reliability Agent is reviewing your request.",
        )

        while tool_call_count < self.max_tool_calls:
            response = self.provider.generate_with_tools(
                messages=messages,
                max_output_tokens=max_output_tokens,
                tools=self.registry.definitions,
                exchanges=exchanges,
            )

            if not response.tool_calls:
                if response.content:
                    if exchanges:
                        report_progress(
                            progress,
                            stage="synthesizing",
                            message=(
                                "Reliability Agent is consolidating the "
                                "findings."
                            ),
                        )
                    return response.content

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
        final_response = self.provider.generate_with_tools(
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=(),
            exchanges=exchanges,
        )

        if final_response.content:
            return final_response.content

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
