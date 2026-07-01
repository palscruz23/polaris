from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.orm import Session

from app.agents.defect_elimination_agent import DefectEliminationAgent
from app.agents.maintenance_strategy_agent import MaintenanceStrategyAgent
from app.models import ScheduledReviewDelivery, ScheduledReviewRun
from app.services.scheduled_review_report_builder import (
    ScheduledReviewReport,
    ScheduledReviewReportBuilder,
)


ScheduledReviewTemplateId = Literal[
    "breakdown_strategy_gap",
    "bad_actor_watchlist",
    "maintenance_strategy_health_check",
]

TEMPLATE_TITLES: dict[str, str] = {
    "breakdown_strategy_gap": "Breakdown Strategy Gap Review",
    "bad_actor_watchlist": "Bad Actor Watchlist",
    "maintenance_strategy_health_check": "Maintenance Strategy Health Check",
}


class ScheduledReviewService:
    def __init__(
        self,
        session: Session,
        report_builder: ScheduledReviewReportBuilder | None = None,
        delivery_service=None,
    ):
        self.session = session
        self.report_builder = report_builder or ScheduledReviewReportBuilder()
        self.delivery_service = delivery_service

    def run_template(
        self,
        template_id: ScheduledReviewTemplateId,
        lookback_days: int,
        now: datetime | None = None,
    ) -> ScheduledReviewRun:
        if template_id not in TEMPLATE_TITLES:
            raise ValueError(f"Unsupported scheduled review template: {template_id}")
        window_start_at, window_end_at = resolve_review_window(lookback_days, now)
        run = ScheduledReviewRun(
            template_id=template_id,
            status="running",
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        self.session.add(run)
        self.session.commit()

        try:
            report = self._build_report(template_id, window_start_at, window_end_at)
            run.report_markdown = report.markdown
            run.summary_json = report.summary_json
            if self.delivery_service is not None:
                try:
                    response = self.delivery_service.send(report.markdown)
                    run.deliveries.append(
                        ScheduledReviewDelivery(
                            provider="teams",
                            status="sent",
                            provider_response_json=response,
                        )
                    )
                    run.status = "succeeded"
                except Exception as delivery_error:
                    run.deliveries.append(
                        ScheduledReviewDelivery(
                            provider="teams",
                            status="failed",
                            error_message=str(delivery_error),
                        )
                    )
                    run.status = "partially_succeeded"
            else:
                run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(UTC)
            raise
        finally:
            self.session.commit()

        return run

    def _build_report(
        self,
        template_id: str,
        window_start_at: datetime,
        window_end_at: datetime,
    ) -> ScheduledReviewReport:
        if template_id == "breakdown_strategy_gap":
            return self._build_breakdown_strategy_gap_report(
                window_start_at,
                window_end_at,
            )
        if template_id == "bad_actor_watchlist":
            return self._build_bad_actor_watchlist_report(
                window_start_at,
                window_end_at,
            )
        return self._build_maintenance_strategy_health_check_report(
            window_start_at,
            window_end_at,
        )

    def _build_breakdown_strategy_gap_report(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ) -> ScheduledReviewReport:
        defect_findings = DefectEliminationAgent(self.session).analyze(
            intent="rank_failure_mode_bad_actors",
            bad_actor_limit=10,
            repeat_failure_limit=10,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        equipment_numbers = [
            finding.equipment_number
            for finding in defect_findings.failure_mode_bad_actors[:10]
        ]
        strategy_findings = MaintenanceStrategyAgent(self.session).analyze(
            intent="detect_gaps",
            equipment_numbers=equipment_numbers,
            maximum_assets=10,
        )
        key_findings = [
            f"{finding.equipment_number}: {finding.failure_mode} "
            f"({finding.repeat_work_order_count} repeat work orders)"
            for finding in defect_findings.failure_mode_bad_actors[:5]
        ]
        recommended_actions = [
            review.recommendations[0].suggestion
            for review in strategy_findings.asset_reviews
            if review.recommendations
        ][:5]
        evidence = [
            finding.evidence
            for finding in defect_findings.failure_mode_bad_actors[:5]
            if finding.evidence
        ]
        return self.report_builder.build(
            template_id="breakdown_strategy_gap",
            title=TEMPLATE_TITLES["breakdown_strategy_gap"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary=(
                "Reviewed recent breakdown-like work orders for strategy "
                "coverage gaps."
            ),
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            evidence=evidence,
            limitations=strategy_findings.limitations,
        )

    def _build_bad_actor_watchlist_report(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ) -> ScheduledReviewReport:
        findings = DefectEliminationAgent(self.session).build_overview(
            bad_actor_limit=10,
            repeat_failure_limit=10,
            window_start_at=window_start_at,
            window_end_at=window_end_at,
        )
        key_findings = [
            f"{finding.equipment_number}: downtime={finding.total_downtime_hours}, "
            f"cost={finding.total_cost}, corrective events="
            f"{finding.corrective_event_count}"
            for finding in findings.bad_actors[:5]
        ]
        evidence = [
            finding.evidence
            for finding in findings.repeat_failures[:5]
            if finding.evidence
        ]
        return self.report_builder.build(
            template_id="bad_actor_watchlist",
            title=TEMPLATE_TITLES["bad_actor_watchlist"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary="Reviewed bad actors and repeat failures.",
            key_findings=key_findings,
            recommended_actions=findings.recommendations[:5],
            evidence=evidence,
            limitations=[],
        )

    def _build_maintenance_strategy_health_check_report(
        self,
        window_start_at: datetime,
        window_end_at: datetime,
    ) -> ScheduledReviewReport:
        findings = MaintenanceStrategyAgent(self.session).review(maximum_assets=10)
        key_findings = [
            f"{review.profile.equipment_number}: "
            f"{len(review.strategy_gaps)} strategy gap(s), "
            f"{len(review.frequency_risks)} frequency risk(s)"
            for review in findings.asset_reviews
        ][:5]
        recommended_actions = [
            recommendation.suggestion
            for review in findings.asset_reviews
            for recommendation in review.recommendations
        ][:5]
        evidence = [
            gap.evidence
            for review in findings.asset_reviews
            for gap in review.strategy_gaps
        ][:5]
        return self.report_builder.build(
            template_id="maintenance_strategy_health_check",
            title=TEMPLATE_TITLES["maintenance_strategy_health_check"],
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            summary="Reviewed maintenance strategy health for high-risk assets.",
            key_findings=key_findings,
            recommended_actions=recommended_actions,
            evidence=evidence,
            limitations=findings.limitations,
        )


def resolve_review_window(
    lookback_days: int,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    end = now or datetime.now(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return end - timedelta(days=lookback_days), end
