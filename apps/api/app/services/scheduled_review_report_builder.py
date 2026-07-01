from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScheduledReviewReport:
    markdown: str
    summary_json: dict


class ScheduledReviewReportBuilder:
    def build(
        self,
        template_id: str,
        title: str,
        window_start_at: datetime,
        window_end_at: datetime,
        summary: str,
        key_findings: list[str],
        recommended_actions: list[str],
        evidence: list[str],
        limitations: list[str],
    ) -> ScheduledReviewReport:
        markdown = "\n".join(
            [
                f"# {title}",
                "",
                (
                    "Window: "
                    f"{window_start_at.isoformat()} to {window_end_at.isoformat()}"
                ),
                "",
                "## Executive summary",
                summary,
                "",
                "## Key findings",
                *_bullet_lines(key_findings),
                "",
                "## Recommended actions",
                *_bullet_lines(recommended_actions),
                "",
                "## Evidence",
                *_bullet_lines(evidence),
                "",
                "## Data limitations",
                *_bullet_lines(limitations),
                "",
            ]
        )
        return ScheduledReviewReport(
            markdown=markdown,
            summary_json={
                "template_id": template_id,
                "title": title,
                "window_start_at": window_start_at.isoformat(),
                "window_end_at": window_end_at.isoformat(),
                "finding_count": len(key_findings),
                "recommended_action_count": len(recommended_actions),
                "evidence_count": len(evidence),
            },
        )


def _bullet_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- None."]
    return [f"- {value}" for value in values]
