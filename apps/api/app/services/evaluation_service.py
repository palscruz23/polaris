import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.agent_run import AgentRun
from app.models.evaluation import EvalCase, EvalCaseResult, EvalRun, EvalSuite
from app.providers.base import ChatProvider
from app.repositories.conversation_repository import ConversationRepository
from app.services.conversation_chat_service import ConversationChatService
from app.services.reliability_agent_orchestrator import ReliabilityAgentOrchestrator


@dataclass(frozen=True)
class EvalCaseDefinition:
    name: str
    prompt: str
    expectations: dict
    conversation_memory: str | None = None
    rubric: dict | None = None
    tags: list[str] | None = None


@dataclass(frozen=True)
class EvalRunSummary:
    eval_run_id: uuid.UUID
    status: str
    case_count: int
    passed_count: int
    failed_count: int
    aggregate_score: float | None


class EvaluationService:
    def __init__(
        self,
        session: Session,
        provider: ChatProvider,
        orchestrator: ReliabilityAgentOrchestrator | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.orchestrator = orchestrator

    def upsert_suite(
        self,
        *,
        name: str,
        description: str | None,
        cases: Sequence[EvalCaseDefinition],
    ) -> EvalSuite:
        suite = self.session.scalar(
            select(EvalSuite).where(EvalSuite.name == name)
        )
        if suite is None:
            suite = EvalSuite(name=name, description=description)
            self.session.add(suite)
            self.session.commit()
            self.session.refresh(suite)
        else:
            suite.description = description
            suite.updated_at = datetime.now(UTC)
            self.session.commit()

        for case_definition in cases:
            existing_case = self.session.scalar(
                select(EvalCase).where(
                    EvalCase.suite_id == suite.id,
                    EvalCase.name == case_definition.name,
                )
            )
            if existing_case is None:
                self.session.add(
                    EvalCase(
                        suite_id=suite.id,
                        name=case_definition.name,
                        prompt=case_definition.prompt,
                        conversation_memory=case_definition.conversation_memory,
                        expectations=case_definition.expectations,
                        rubric=case_definition.rubric,
                        tags=case_definition.tags,
                    )
                )
            else:
                existing_case.prompt = case_definition.prompt
                existing_case.conversation_memory = (
                    case_definition.conversation_memory
                )
                existing_case.expectations = case_definition.expectations
                existing_case.rubric = case_definition.rubric
                existing_case.tags = case_definition.tags
                existing_case.is_active = True
                existing_case.updated_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(suite)
        return suite

    def run_suite(
        self,
        *,
        suite_name: str,
        git_commit: str | None = None,
        dataset_version: str | None = None,
        run_metadata: dict | None = None,
    ) -> EvalRunSummary:
        suite = self.session.scalar(
            select(EvalSuite)
            .where(EvalSuite.name == suite_name)
            .options(selectinload(EvalSuite.cases))
        )
        if suite is None:
            raise ValueError(f"Evaluation suite '{suite_name}' does not exist.")

        active_cases = [case for case in suite.cases if case.is_active]
        eval_run = EvalRun(
            suite_id=suite.id,
            provider=self.provider.name,
            model=self.provider.model,
            git_commit=git_commit,
            dataset_version=dataset_version,
            case_count=len(active_cases),
            run_metadata=run_metadata,
        )
        self.session.add(eval_run)
        self.session.commit()
        self.session.refresh(eval_run)

        try:
            for eval_case in active_cases:
                self._run_case(eval_run=eval_run, eval_case=eval_case)

            return self._complete_run(eval_run)
        except Exception as error:
            eval_run.status = "failed"
            eval_run.error_type = type(error).__name__
            eval_run.error_message = str(error)
            eval_run.completed_at = datetime.now(UTC)
            self.session.commit()
            raise

    def _run_case(
        self,
        *,
        eval_run: EvalRun,
        eval_case: EvalCase,
    ) -> None:
        conversation = ConversationRepository(self.session).create(
            title=f"Eval: {eval_case.name}",
        )
        if eval_case.conversation_memory:
            conversation.memory_markdown = eval_case.conversation_memory
            self.session.commit()

        service = ConversationChatService(
            self.session,
            self.provider,
            orchestrator=self.orchestrator,
        )

        try:
            user_message, assistant_message, memory_status = service.respond(
                conversation.id,
                eval_case.prompt,
            )
            agent_run = self._get_agent_run(assistant_message.id)
            trace = self._build_trace(
                agent_run=agent_run,
                assistant_metadata=assistant_message.metadata_,
                memory_status=memory_status,
            )
            scoring = score_eval_case(
                expectations=eval_case.expectations,
                assistant_answer=assistant_message.content,
                trace=trace,
            )

            self.session.add(
                EvalCaseResult(
                    eval_run_id=eval_run.id,
                    eval_case_id=eval_case.id,
                    conversation_id=conversation.id,
                    user_message_id=user_message.id,
                    assistant_message_id=assistant_message.id,
                    agent_run_id=agent_run.id if agent_run is not None else None,
                    status="passed" if scoring["passed"] else "failed",
                    score=scoring["score"],
                    scores=scoring["scores"],
                    checks=scoring["checks"],
                    trace=trace,
                    assistant_answer=assistant_message.content,
                    failure_category=scoring["failure_category"],
                )
            )
            self.session.commit()
        except Exception as error:
            self.session.add(
                EvalCaseResult(
                    eval_run_id=eval_run.id,
                    eval_case_id=eval_case.id,
                    conversation_id=conversation.id,
                    status="error",
                    score=0.0,
                    scores={},
                    checks=[],
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
            )
            self.session.commit()

    def _get_agent_run(
        self,
        assistant_message_id: uuid.UUID,
    ) -> AgentRun | None:
        return self.session.scalar(
            select(AgentRun)
            .where(AgentRun.assistant_message_id == assistant_message_id)
            .options(selectinload(AgentRun.model_calls))
        )

    @staticmethod
    def _build_trace(
        *,
        agent_run: AgentRun | None,
        assistant_metadata: dict | None,
        memory_status: str,
    ) -> dict:
        return {
            "agent_run": (
                {
                    "id": str(agent_run.id),
                    "status": agent_run.status,
                    "provider": agent_run.provider,
                    "model": agent_run.model,
                    "tool_call_count": agent_run.tool_call_count,
                    "model_call_count": agent_run.model_call_count,
                    "total_latency_ms": agent_run.total_latency_ms,
                }
                if agent_run is not None
                else None
            ),
            "model_calls": (
                [
                    {
                        "sequence_number": call.sequence_number,
                        "call_type": call.call_type,
                        "status": call.status,
                        "latency_ms": call.latency_ms,
                        "requested_tool_count": call.requested_tool_count,
                        "response_tool_call_count": (
                            call.response_tool_call_count
                        ),
                    }
                    for call in agent_run.model_calls
                ]
                if agent_run is not None
                else []
            ),
            "tool_calls": (
                assistant_metadata.get("tool_calls", [])
                if assistant_metadata
                else []
            ),
            "internal_calls": (
                assistant_metadata.get("internal_calls", [])
                if assistant_metadata
                else []
            ),
            "memory_status": memory_status,
        }

    def _complete_run(self, eval_run: EvalRun) -> EvalRunSummary:
        results = list(
            self.session.scalars(
                select(EvalCaseResult).where(
                    EvalCaseResult.eval_run_id == eval_run.id
                )
            ).all()
        )
        passed_count = sum(1 for result in results if result.status == "passed")
        failed_count = sum(
            1 for result in results if result.status in {"failed", "error"}
        )
        aggregate_score = (
            sum(result.score for result in results) / len(results)
            if results
            else None
        )

        eval_run.status = "completed"
        eval_run.case_count = len(results)
        eval_run.passed_count = passed_count
        eval_run.failed_count = failed_count
        eval_run.aggregate_score = aggregate_score
        eval_run.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(eval_run)

        return EvalRunSummary(
            eval_run_id=eval_run.id,
            status=eval_run.status,
            case_count=eval_run.case_count,
            passed_count=eval_run.passed_count,
            failed_count=eval_run.failed_count,
            aggregate_score=eval_run.aggregate_score,
        )


def score_eval_case(
    *,
    expectations: dict,
    assistant_answer: str,
    trace: dict,
) -> dict:
    checks: list[dict] = []
    tool_calls = trace.get("tool_calls", [])
    model_calls = trace.get("model_calls", [])
    answer_lower = assistant_answer.lower()

    expected_tool_calls = expectations.get("expected_tool_calls", [])
    if expectations.get("no_tool_calls"):
        checks.append(
            _check(
                "routing.no_tool_calls",
                not tool_calls,
                "routing",
                {"actual_count": len(tool_calls)},
            )
        )

    for index, expected_call in enumerate(expected_tool_calls, start=1):
        matching_call = _find_matching_tool_call(tool_calls, expected_call)
        check_prefix = f"routing.tool_call_{index}"
        checks.append(
            _check(
                check_prefix,
                matching_call is not None,
                "routing",
                {
                    "expected_tool": expected_call.get("tool"),
                    "expected_target_agent": expected_call.get("target_agent"),
                },
            )
        )
        if matching_call is None:
            continue

        if "intent" in expected_call or "allowed_intents" in expected_call:
            actual_intent = matching_call.get("arguments", {}).get("intent")
            allowed_intents = expected_call.get("allowed_intents") or [
                expected_call.get("intent")
            ]
            checks.append(
                _check(
                    f"{check_prefix}.intent",
                    actual_intent in allowed_intents,
                    "intent",
                    {
                        "actual_intent": actual_intent,
                        "allowed_intents": allowed_intents,
                    },
                )
            )

        for sub_tool in expected_call.get("required_sub_tools", []):
            actual_sub_tools = [
                sub_call.get("tool")
                for sub_call in matching_call.get("sub_calls", [])
            ]
            checks.append(
                _check(
                    f"{check_prefix}.sub_tool.{sub_tool}",
                    sub_tool in actual_sub_tools,
                    "tools",
                    {
                        "expected_sub_tool": sub_tool,
                        "actual_sub_tools": actual_sub_tools,
                    },
                )
            )

        for term in expected_call.get("required_result_terms", []):
            result_text = str(matching_call.get("result", "")).lower()
            checks.append(
                _check(
                    f"{check_prefix}.result_term.{term}",
                    term.lower() in result_text,
                    "evidence",
                    {"term": term},
                )
            )

    for term in expectations.get("required_answer_terms", []):
        checks.append(
            _check(
                f"answer.required_term.{term}",
                term.lower() in answer_lower,
                "answer",
                {"term": term},
            )
        )

    for term in expectations.get("forbidden_answer_terms", []):
        checks.append(
            _check(
                f"answer.forbidden_term.{term}",
                term.lower() not in answer_lower,
                "answer",
                {"term": term},
            )
        )

    actual_call_types = [call.get("call_type") for call in model_calls]
    for call_type in expectations.get("required_model_call_types", []):
        checks.append(
            _check(
                f"trace.model_call.{call_type}",
                call_type in actual_call_types,
                "trace",
                {
                    "expected_call_type": call_type,
                    "actual_call_types": actual_call_types,
                },
            )
        )

    if not checks:
        checks.append(
            _check(
                "case.has_expectations",
                False,
                "configuration",
                {"message": "Eval case has no scorable expectations."},
            )
        )

    scores = _scores_by_category(checks)
    passed = all(check["passed"] for check in checks)
    score = sum(check["score"] for check in checks) / len(checks)
    failure_category = None
    if not passed:
        failure_category = next(
            check["category"] for check in checks if not check["passed"]
        )

    return {
        "passed": passed,
        "score": score,
        "scores": scores,
        "checks": checks,
        "failure_category": failure_category,
    }


def _find_matching_tool_call(
    tool_calls: Sequence[dict],
    expected_call: dict,
) -> dict | None:
    for tool_call in tool_calls:
        if expected_call.get("tool") and (
            tool_call.get("tool") != expected_call["tool"]
        ):
            continue
        if expected_call.get("target_agent") and (
            tool_call.get("target_agent") != expected_call["target_agent"]
        ):
            continue
        return tool_call
    return None


def _check(
    name: str,
    passed: bool,
    category: str,
    details: dict,
) -> dict:
    return {
        "name": name,
        "category": category,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "details": details,
    }


def _scores_by_category(checks: Sequence[dict]) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for check in checks:
        grouped[check["category"]].append(check["score"])

    return {
        category: sum(scores) / len(scores)
        for category, scores in grouped.items()
    }
