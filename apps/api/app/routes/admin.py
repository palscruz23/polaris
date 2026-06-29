import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_database_session
from app.dependencies.auth import CurrentAdminUser
from app.models.evaluation import EvalCaseResult, EvalRun
from app.models.user_login_event import UserLoginEvent
from app.schemas.admin import (
    AdminEvalCaseResultResponse,
    AdminEvaluationDashboardResponse,
    AdminEvalRunDetailResponse,
    AdminEvalSuiteDashboardResponse,
    AdminEvalRunSummaryResponse,
    AdminLoginEventResponse,
    AdminUserLoginSummaryResponse,
    AdminUsersDashboardResponse,
)
from app.schemas.auth import AuthUserResponse

router = APIRouter(prefix="/admin", tags=["admin"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get(
    "/evaluations",
    response_model=AdminEvaluationDashboardResponse,
)
def get_evaluation_dashboard(
    session: DatabaseSession,
    user: CurrentAdminUser,
) -> AdminEvaluationDashboardResponse:
    runs = _latest_eval_runs(session)
    latest_run = runs[0] if runs else None
    suite_groups = _suite_dashboard_groups(runs)

    return AdminEvaluationDashboardResponse(
        viewer=AuthUserResponse.model_validate(user),
        admin_emails_configured=bool(settings.admin_emails),
        runs=[_run_summary(run) for run in runs],
        latest_run=(
            _run_detail(latest_run)
            if latest_run is not None
            else None
        ),
        suites=suite_groups,
    )


@router.get(
    "/evaluations/runs/{run_id}",
    response_model=AdminEvalRunDetailResponse,
)
def get_evaluation_run(
    run_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentAdminUser,
) -> AdminEvalRunDetailResponse:
    del user
    run = session.scalar(
        select(EvalRun)
        .where(EvalRun.id == run_id)
        .options(
            selectinload(EvalRun.suite),
            selectinload(EvalRun.results)
            .selectinload(EvalCaseResult.case),
        )
    )
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation run not found.",
        )

    return _run_detail(run)


@router.get(
    "/users",
    response_model=AdminUsersDashboardResponse,
)
def get_users_dashboard(
    session: DatabaseSession,
    user: CurrentAdminUser,
) -> AdminUsersDashboardResponse:
    del user
    login_events = list(
        session.scalars(
            select(UserLoginEvent)
            .order_by(UserLoginEvent.created_at.desc())
            .limit(100)
        ).all()
    )
    login_counts = session.execute(
        select(
            UserLoginEvent.user_id,
            func.count(UserLoginEvent.id).label("login_count"),
            func.max(UserLoginEvent.created_at).label("latest_login_at"),
        )
        .group_by(UserLoginEvent.user_id)
        .order_by(desc("latest_login_at"))
        .limit(100)
    ).all()

    return AdminUsersDashboardResponse(
        logins=[
            AdminLoginEventResponse(
                id=login.id,
                user_id=login.user_id,
                created_at=login.created_at,
            )
            for login in login_events
        ],
        user_login_counts=[
            AdminUserLoginSummaryResponse(
                user_id=row.user_id,
                login_count=row.login_count,
                latest_login_at=row.latest_login_at,
            )
            for row in login_counts
        ],
    )


def _latest_eval_runs(
    session: Session,
    limit: int = 20,
) -> list[EvalRun]:
    return list(
        session.scalars(
            select(EvalRun)
            .options(
                selectinload(EvalRun.suite),
                selectinload(EvalRun.results)
                .selectinload(EvalCaseResult.case),
            )
            .order_by(EvalRun.started_at.desc())
            .limit(limit)
        ).all()
    )


def _run_summary(run: EvalRun) -> AdminEvalRunSummaryResponse:
    return AdminEvalRunSummaryResponse(
        id=run.id,
        suite_id=run.suite_id,
        suite_name=run.suite.name,
        provider=run.provider,
        model=run.model,
        status=run.status,
        case_count=run.case_count,
        passed_count=run.passed_count,
        failed_count=run.failed_count,
        aggregate_score=run.aggregate_score,
        git_commit=run.git_commit,
        dataset_version=run.dataset_version,
        run_metadata=run.run_metadata,
        error_type=run.error_type,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _run_detail(run: EvalRun) -> AdminEvalRunDetailResponse:
    summary = _run_summary(run).model_dump()
    results = sorted(
        run.results,
        key=lambda result: result.case.name if result.case else "",
    )

    return AdminEvalRunDetailResponse(
        **summary,
        results=[
            AdminEvalCaseResultResponse(
                id=result.id,
                case_id=result.eval_case_id,
                case_name=result.case.name,
                prompt=result.case.prompt,
                status=result.status,
                score=result.score,
                scores=result.scores,
                checks=result.checks,
                failure_category=result.failure_category,
                assistant_answer=result.assistant_answer,
                trace=result.trace,
                error_type=result.error_type,
                error_message=result.error_message,
                conversation_id=result.conversation_id,
                agent_run_id=result.agent_run_id,
                created_at=result.created_at,
            )
            for result in results
            if result.case is not None
        ],
    )


def _suite_dashboard_groups(
    runs: list[EvalRun],
) -> list[AdminEvalSuiteDashboardResponse]:
    suite_order = ["smoke", "prod"]
    grouped: dict[str, list[EvalRun]] = {name: [] for name in suite_order}
    for run in runs:
        grouped.setdefault(run.suite.name, []).append(run)

    suite_names = [
        *suite_order,
        *sorted(name for name in grouped if name not in suite_order),
    ]

    return [
        AdminEvalSuiteDashboardResponse(
            suite_name=suite_name,
            runs=[_run_summary(run) for run in grouped[suite_name]],
            latest_run=(
                _run_detail(grouped[suite_name][0])
                if grouped[suite_name]
                else None
            ),
        )
        for suite_name in suite_names
    ]
