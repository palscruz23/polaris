from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.database import get_database_session
from app.schemas.defect_elimination import DefectEliminationOverviewResponse


router = APIRouter(
    prefix="/defect-elimination",
    tags=["defect elimination"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "/overview",
    response_model=DefectEliminationOverviewResponse,
)
def get_defect_elimination_overview(
    session: DatabaseSession,
    bad_actor_limit: Annotated[int, Query(ge=1, le=50)] = 10,
    repeat_failure_limit: Annotated[int, Query(ge=1, le=50)] = 10,
    minimum_repeat_occurrences: Annotated[int, Query(ge=2, le=20)] = 2,
) -> DefectEliminationOverviewResponse:
    agent = DefectEliminationAgent(session)
    findings = agent.build_overview(
        bad_actor_limit=bad_actor_limit,
        repeat_failure_limit=repeat_failure_limit,
        minimum_repeat_occurrences=minimum_repeat_occurrences,
    )

    return DefectEliminationOverviewResponse(
        summary=findings.summary,
        bad_actors=findings.bad_actors,
        repeat_failures=findings.repeat_failures,
        mtbf_metrics=findings.mtbf_metrics,
        weibull_analysis=findings.weibull_analysis,
        rca_evidence_plans=findings.rca_evidence_plans,
        five_whys=findings.five_whys,
        rca_templates=findings.rca_templates,
        charters=findings.charters,
        recommendations=findings.recommendations,
    )
