import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.orchestration import AgentModelCallTrace
from app.models.agent_run import AgentRun
from app.models.model_call import ModelCall


class ObservabilityRepository:
    def __init__(self, session: Session):
        self.session = session

    def start_agent_run(
        self,
        *,
        conversation_id: uuid.UUID,
        user_message_id: uuid.UUID,
        provider: str,
        model: str,
        input_tokens_estimate: int,
    ) -> AgentRun:
        agent_run = AgentRun(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            provider=provider,
            model=model,
            input_tokens_estimate=input_tokens_estimate,
        )
        self.session.add(agent_run)
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run

    def record_model_call(
        self,
        *,
        agent_run: AgentRun,
        trace: AgentModelCallTrace,
    ) -> ModelCall:
        model_call = ModelCall(
            agent_run_id=agent_run.id,
            sequence_number=agent_run.model_call_count + 1,
            call_type=trace.call_type,
            provider=agent_run.provider,
            model=agent_run.model,
            status=trace.status,
            latency_ms=trace.latency_ms,
            input_tokens_estimate=trace.input_tokens_estimate,
            output_tokens_estimate=trace.output_tokens_estimate,
            max_output_tokens=trace.max_output_tokens,
            requested_tool_count=trace.requested_tool_count,
            response_tool_call_count=trace.response_tool_call_count,
            error_type=trace.error_type,
            error_message=trace.error_message,
        )
        agent_run.model_call_count += 1
        self.session.add(model_call)
        self.session.commit()
        self.session.refresh(model_call)
        return model_call

    def complete_agent_run(
        self,
        *,
        agent_run: AgentRun,
        assistant_message_id: uuid.UUID,
        total_latency_ms: int,
        output_tokens_estimate: int,
        tool_call_count: int,
        tool_metadata: dict | None,
    ) -> AgentRun:
        agent_run.assistant_message_id = assistant_message_id
        agent_run.status = "completed"
        agent_run.total_latency_ms = total_latency_ms
        agent_run.output_tokens_estimate = output_tokens_estimate
        agent_run.tool_call_count = tool_call_count
        agent_run.tool_metadata = tool_metadata
        agent_run.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run

    def fail_agent_run(
        self,
        *,
        agent_run: AgentRun,
        total_latency_ms: int,
        error: Exception,
    ) -> AgentRun:
        agent_run.status = "failed"
        agent_run.total_latency_ms = total_latency_ms
        agent_run.error_type = type(error).__name__
        agent_run.error_message = str(error)
        agent_run.completed_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run
