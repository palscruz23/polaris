from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Equipment


@dataclass(frozen=True)
class EquipmentSummary:
    total_matching: int
    returned_count: int
    offset: int
    limit: int
    has_more: bool
    status_counts: dict[str, int]
    equipment_type_counts: dict[str, int]


@dataclass(frozen=True)
class EquipmentRecord:
    equipment_number: str
    description: str | None
    functional_location: str | None
    equipment_type: str | None
    system: str | None
    criticality: str | None
    status: str
    parent_functional_location: str | None


@dataclass(frozen=True)
class EquipmentSearchResult:
    summary: EquipmentSummary
    equipment: list[EquipmentRecord]


class EquipmentSearchTool:
    def run(
        self,
        session: Session,
        *,
        query: str | None = None,
        equipment_type: str | None = None,
        functional_location: str | None = None,
        criticality: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> EquipmentSearchResult:
        filters = self._filters(
            query=query,
            equipment_type=equipment_type,
            functional_location=functional_location,
            criticality=criticality,
            status=status,
        )
        total_matching = session.scalar(
            select(func.count()).select_from(Equipment).where(*filters)
        ) or 0
        rows = list(
            session.scalars(
                select(Equipment)
                .where(*filters)
                .order_by(Equipment.equipment_number)
                .offset(offset)
                .limit(limit)
            ).all()
        )

        return EquipmentSearchResult(
            summary=EquipmentSummary(
                total_matching=total_matching,
                returned_count=len(rows),
                offset=offset,
                limit=limit,
                has_more=offset + len(rows) < total_matching,
                status_counts=self._group_counts(
                    session,
                    Equipment.status,
                    filters,
                    "unknown",
                ),
                equipment_type_counts=self._group_counts(
                    session,
                    Equipment.equipment_type,
                    filters,
                    "unclassified",
                ),
            ),
            equipment=[
                EquipmentRecord(
                    equipment_number=item.equipment_number,
                    description=item.description,
                    functional_location=item.functional_location,
                    equipment_type=item.equipment_type,
                    system=item.system,
                    criticality=item.criticality,
                    status=item.status,
                    parent_functional_location=(
                        item.parent_functional_location
                    ),
                )
                for item in rows
            ],
        )

    @staticmethod
    def _filters(
        *,
        query: str | None,
        equipment_type: str | None,
        functional_location: str | None,
        criticality: str | None,
        status: str | None,
    ) -> list[object]:
        filters: list[object] = []

        if query:
            pattern = f"%{query.strip()}%"
            filters.append(
                or_(
                    Equipment.equipment_number.ilike(pattern),
                    Equipment.description.ilike(pattern),
                    Equipment.equipment_type.ilike(pattern),
                    Equipment.functional_location.ilike(pattern),
                    Equipment.system.ilike(pattern),
                    Equipment.criticality.ilike(pattern),
                )
            )
        if equipment_type:
            filters.append(
                func.lower(Equipment.equipment_type)
                == equipment_type.strip().lower()
            )
        if functional_location:
            filters.append(
                Equipment.functional_location.ilike(
                    f"%{functional_location.strip()}%"
                )
            )
        if criticality:
            filters.append(
                func.lower(Equipment.criticality)
                == criticality.strip().lower()
            )
        if status:
            filters.append(
                func.lower(Equipment.status) == status.strip().lower()
            )

        return filters

    @staticmethod
    def _group_counts(
        session: Session,
        column: object,
        filters: list[object],
        fallback: str,
    ) -> dict[str, int]:
        grouped = session.execute(
            select(column, func.count())
            .select_from(Equipment)
            .where(*filters)
            .group_by(column)
            .order_by(column)
        ).all()

        return {
            value or fallback: count
            for value, count in grouped
        }
