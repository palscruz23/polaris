from types import SimpleNamespace

from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentToolDefinition,
    AgentToolExchange,
    AgentToolResult,
)
from app.providers.models import get_available_model
from app.providers.openrouter import OpenRouterProvider


class RecordingCompletions:
    def __init__(self, responses: list[SimpleNamespace]):
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def create(self, **request: object) -> SimpleNamespace:
        self.requests.append(request)
        return self.responses.pop(0)


def test_openrouter_provider_translates_tool_calls_and_results() -> None:
    tool_call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(
            name="analyze_defect_elimination",
            arguments='{"bad_actor_limit": 3}',
        ),
    )
    completions = RecordingCompletions(
        [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[tool_call],
                        )
                    )
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="P-101 is the leading bad actor.",
                            tool_calls=None,
                        )
                    )
                ]
            ),
        ]
    )
    provider = OpenRouterProvider.__new__(OpenRouterProvider)
    provider.selected_model = get_available_model(
        "qwen/qwen3-235b-a22b-2507"
    )
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    definition = AgentToolDefinition(
        name="analyze_defect_elimination",
        description="Analyze failures.",
        input_schema={"type": "object", "properties": {}},
    )
    messages = [ChatMessage(role="user", content="Find bad actors.")]

    first_response = provider.generate_with_tools(
        messages=messages,
        max_output_tokens=500,
        tools=(definition,),
    )
    exchange = AgentToolExchange(
        call=first_response.tool_calls[0],
        result=AgentToolResult(
            call_id="call-1",
            tool_name="analyze_defect_elimination",
            content='{"bad_actors":["P-101"]}',
        ),
    )
    final_response = provider.generate_with_tools(
        messages=messages,
        max_output_tokens=500,
        tools=(definition,),
        exchanges=(exchange,),
    )

    assert first_response.tool_calls[0].arguments == {
        "bad_actor_limit": 3
    }
    assert final_response.content == "P-101 is the leading bad actor."
    assert completions.requests[0]["model"] == "qwen/qwen3-235b-a22b-2507"
    assert completions.requests[0]["tools"][0]["function"]["name"] == (
        "analyze_defect_elimination"
    )
    transcript = completions.requests[1]["messages"]
    assert [message["role"] for message in transcript] == [
        "user",
        "assistant",
        "tool",
    ]
    assert transcript[-1]["tool_call_id"] == "call-1"
