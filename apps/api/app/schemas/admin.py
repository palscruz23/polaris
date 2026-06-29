import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.auth import AuthUserResponse


class AdminEvalCaseResultResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    case_name: str
    prompt: str
    status: str
    score: float
    scores: dict[str, float]
    checks: list[dict[str, Any]]
    failure_category: str | None
    assistant_answer: str | None
    trace: dict[str, Any] | None
    error_type: str | None
    error_message: str | None
    conversation_id: uuid.UUID | None
    agent_run_id: uuid.UUID | None
    created_at: datetime


class AdminEvalRunSummaryResponse(BaseModel):
    id: uuid.UUID
    suite_id: uuid.UUID
    suite_name: str
    provider: str
    model: str
    status: str
    case_count: int
    passed_count: int
    failed_count: int
    aggregate_score: float | None
    git_commit: str | None
    dataset_version: str | None
    run_metadata: dict[str, Any] | None
    error_type: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class AdminEvalRunDetailResponse(AdminEvalRunSummaryResponse):
    results: list[AdminEvalCaseResultResponse]


class AdminEvalSuiteDashboardResponse(BaseModel):
    suite_name: str
    runs: list[AdminEvalRunSummaryResponse]
    latest_run: AdminEvalRunDetailResponse | None


class AdminEvaluationDashboardResponse(BaseModel):
    viewer: AuthUserResponse
    admin_emails_configured: bool
    runs: list[AdminEvalRunSummaryResponse]
    latest_run: AdminEvalRunDetailResponse | None
    suites: list[AdminEvalSuiteDashboardResponse]


class AdminLoginEventResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class AdminUserLoginSummaryResponse(BaseModel):
    user_id: uuid.UUID
    login_count: int
    latest_login_at: datetime | None


class AdminUsersDashboardResponse(BaseModel):
    logins: list[AdminLoginEventResponse]
    user_login_counts: list[AdminUserLoginSummaryResponse]
