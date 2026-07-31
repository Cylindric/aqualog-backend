from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Parameter


class DuplicateParameterSlugError(ValueError):
    pass


class ParameterInUseError(ValueError):
    pass


class ParameterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Parameter]:
        return self.session.query(Parameter).order_by(Parameter.slug.asc()).all()

    def get_by_slug(self, slug: str) -> Parameter | None:
        return self.session.query(Parameter).filter(Parameter.slug == slug).one_or_none()

    def create(self, slug: str, display_name: str, description: str | None) -> Parameter:
        parameter = Parameter(slug=slug, display_name=display_name, description=description)
        self.session.add(parameter)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateParameterSlugError("Parameter slug must be unique") from exc
        self.session.refresh(parameter)
        return parameter

    def update_by_slug(self, slug: str, updates: dict[str, str | None]) -> Parameter | None:
        parameter = self.get_by_slug(slug)
        if parameter is None:
            return None

        for key, value in updates.items():
            setattr(parameter, key, value)

        self.session.add(parameter)
        self.session.commit()
        self.session.refresh(parameter)
        return parameter

    def delete_by_slug(self, slug: str) -> bool:
        parameter = self.get_by_slug(slug)
        if parameter is None:
            return False

        self.session.delete(parameter)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ParameterInUseError(
                "Parameter is still referenced by measurements or thresholds"
            ) from exc
        return True
