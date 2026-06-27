import math
from collections.abc import Sequence

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.database import Base
from app.domain.chat import ChatMessage
from app.domain.orchestration import (
    AgentModelCallTrace,
    AgentOrchestrationResponse,
    AgentToolCall,
    AgentToolExchange,
    AgentToolResult,
    SubToolCall,
)
from app.models.evaluation import EvalCaseResult, EvalRun
from app.providers.base import ChatProvider
from app.services.evaluation_service import (
    EvalCaseDefinition,
    EvaluationService,
    score_eval_case,
)


class EvalRecordingProvider(ChatProvider):
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
        del messages, max_output_tokens
        return "# Conversation Memory\n\n## Objective\nRun evaluation."


class EvalMetadataOrchestrator:
    def respond_with_metadata(
        self,
        messages: Sequence[ChatMessage],
        max_output_tokens: int,
        progress=None,
        model_call_observer=None,
    ) -> AgentOrchestrationResponse:
        del messages, max_output_tokens, progress
        if model_call_observer is not None:
            model_call_observer(
                AgentModelCallTrace(
                    call_type="agent_tool_selection",
                    status="completed",
                    latency_ms=10,
                    input_tokens_estimate=120,
                    output_tokens_estimate=20,
                    max_output_tokens=500,
                    requested_tool_count=3,
                    response_tool_call_count=1,
                )
            )
            model_call_observer(
                AgentModelCallTrace(
                    call_type="agent_final_synthesis",
                    status="completed",
                    latency_ms=12,
                    input_tokens_estimate=160,
                    output_tokens_estimate=40,
                    max_output_tokens=500,
                    requested_tool_count=1,
                    response_tool_call_count=0,
                )
            )

        return AgentOrchestrationResponse(
            content="P-101 is the bad actor. Prioritize bearing reliability.",
            tool_calls=(
                AgentToolExchange(
                    call=AgentToolCall(
                        id="call-1",
                        name="analyze_defect_elimination",
                        arguments={"intent": "rank_bad_actors"},
                    ),
                    result=AgentToolResult(
                        call_id="call-1",
                        tool_name="analyze_defect_elimination",
                        content='{"bad_actors":[{"equipment_number":"P-101"}]}',
                        sub_calls=(
                            SubToolCall(
                                specialist="defect_elimination",
                                tool="reliability_metrics",
                                message="Summarize reliability history.",
                            ),
                            SubToolCall(
                                specialist="defect_elimination",
                                tool="bad_actor_analysis",
                                message="Rank bad actors.",
                            ),
                        ),
                    ),
                ),
            ),
        )


def test_score_eval_case_checks_route_intent_tools_answer_and_trace() -> None:
    scoring = score_eval_case(
        expectations={
            "expected_tool_calls": [
                {
                    "tool": "analyze_defect_elimination",
                    "target_agent": "defect_elimination",
                    "intent": "rank_bad_actors",
                    "required_sub_tools": [
                        "reliability_metrics",
                        "bad_actor_analysis",
                    ],
                    "required_result_terms": ["P-101"],
                }
            ],
            "required_answer_terms": ["P-101"],
            "required_model_call_types": ["agent_tool_selection"],
        },
        assistant_answer="P-101 should be treated as the bad actor.",
        trace={
            "model_calls": [{"call_type": "agent_tool_selection"}],
            "tool_calls": [
                {
                    "tool": "analyze_defect_elimination",
                    "target_agent": "defect_elimination",
                    "arguments": {"intent": "rank_bad_actors"},
                    "result": '{"equipment_number":"P-101"}',
                    "sub_calls": [
                        {"tool": "reliability_metrics"},
                        {"tool": "bad_actor_analysis"},
                    ],
                }
            ],
        },
    )

    assert scoring["passed"] is True
    assert scoring["score"] == 1.0
    assert scoring["scores"]["routing"] == 1.0
    assert scoring["scores"]["intent"] == 1.0
    assert scoring["scores"]["tools"] == 1.0


def test_evaluation_service_persists_whole_workflow_result() -> None:
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        provider = EvalRecordingProvider()
        service = EvaluationService(
            session,
            provider,
            orchestrator=EvalMetadataOrchestrator(),  # type: ignore[arg-type]
        )
        service.upsert_suite(
            name="unit-smoke",
            description="Unit test suite.",
            cases=[
                EvalCaseDefinition(
                    name="bad_actor_trace",
                    prompt="Find the bad actor.",
                    expectations={
                        "expected_tool_calls": [
                            {
                                "tool": "analyze_defect_elimination",
                                "target_agent": "defect_elimination",
                                "intent": "rank_bad_actors",
                                "required_sub_tools": [
                                    "reliability_metrics",
                                    "bad_actor_analysis",
                                ],
                            }
                        ],
                        "required_answer_terms": ["P-101"],
                        "required_model_call_types": [
                            "agent_tool_selection",
                            "agent_final_synthesis",
                        ],
                    },
                )
            ],
        )

        summary = service.run_suite(
            suite_name="unit-smoke",
            git_commit="abc123",
            dataset_version="test-seed",
        )

        eval_run = session.get(EvalRun, summary.eval_run_id)
        results = list(
            session.scalars(
                select(EvalCaseResult).where(
                    EvalCaseResult.eval_run_id == summary.eval_run_id
                )
            ).all()
        )

        assert eval_run is not None
        assert eval_run.status == "completed"
        assert eval_run.case_count == 1
        assert eval_run.passed_count == 1
        assert summary.aggregate_score == 1.0
        assert len(results) == 1
        assert results[0].status == "passed"
        assert results[0].conversation_id is not None
        assert results[0].agent_run_id is not None
        assert results[0].trace is not None
        assert results[0].trace["tool_calls"][0]["arguments"] == {
            "intent": "rank_bad_actors"
        }
    finally:
        session.close()
        transaction.rollback()
        connection.close()
