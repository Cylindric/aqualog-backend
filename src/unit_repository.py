from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import ParameterUnit, Unit
from src.unit_slug import slugify_unit


class DuplicateUnitSlugError(ValueError):
    pass


class UnitInUseError(ValueError):
    pass


class UnitRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Unit]:
        return self.session.query(Unit).order_by(Unit.slug.asc()).all()

    def get_by_slug(self, slug: str) -> Unit | None:
        return self.session.query(Unit).filter(Unit.slug == slug.lower()).one_or_none()

    def get_by_unit(self, unit: str) -> Unit | None:
        return self.session.query(Unit).filter(func.lower(Unit.unit) == unit.lower()).one_or_none()

    def create(self, unit: str, display_name: str, description: str | None) -> Unit:
        unit_row = Unit(
            unit=unit,
            slug=slugify_unit(unit),
            display_name=display_name,
            description=description,
        )
        self.session.add(unit_row)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateUnitSlugError("Unit slug must be unique") from exc
        self.session.refresh(unit_row)
        return unit_row

    def update_by_slug(self, slug: str, updates: dict[str, str | None]) -> Unit | None:
        unit = self.get_by_slug(slug)
        if unit is None:
            return None

        for key, value in updates.items():
            setattr(unit, key, value)

        self.session.add(unit)
        self.session.commit()
        self.session.refresh(unit)
        return unit

    def delete_by_slug(self, slug: str) -> bool:
        unit = self.get_by_slug(slug)
        if unit is None:
            return False

        self.session.delete(unit)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise UnitInUseError(
                "Unit is still referenced by measurements or parameter associations"
            ) from exc
        return True

    def list_units_for_parameter(self, parameter_id: uuid.UUID) -> list[Unit]:
        return (
            self.session.query(Unit)
            .join(ParameterUnit, ParameterUnit.unit_id == Unit.id)
            .filter(ParameterUnit.parameter_id == parameter_id)
            .order_by(Unit.slug.asc())
            .all()
        )

    def get_canonical_unit(self, parameter_id: uuid.UUID) -> Unit | None:
        return (
            self.session.query(Unit)
            .join(ParameterUnit, ParameterUnit.unit_id == Unit.id)
            .filter(
                ParameterUnit.parameter_id == parameter_id,
                ParameterUnit.is_canonical.is_(True),
            )
            .one_or_none()
        )

    def is_unit_valid_for_parameter(self, parameter_id: uuid.UUID, unit_id: uuid.UUID) -> bool:
        return (
            self.session.query(ParameterUnit)
            .filter(
                ParameterUnit.parameter_id == parameter_id,
                ParameterUnit.unit_id == unit_id,
            )
            .first()
            is not None
        )
