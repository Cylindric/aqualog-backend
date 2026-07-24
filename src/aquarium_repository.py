from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Aquarium


class DuplicateAquariumNameError(ValueError):
    pass


class AquariumRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _require_owner(self, owner_user_id: str) -> None:
        if not owner_user_id:
            raise ValueError("owner_user_id is required")

    def list_by_owner(self, owner_user_id: str) -> list[Aquarium]:
        self._require_owner(owner_user_id)
        return (
            self.session.query(Aquarium)
            .filter(Aquarium.owner_user_id == owner_user_id)
            .order_by(Aquarium.created_at.asc())
            .all()
        )

    def get_by_id_and_owner(self, aquarium_id: str, owner_user_id: str) -> Aquarium | None:
        self._require_owner(owner_user_id)
        return (
            self.session.query(Aquarium)
            .filter(Aquarium.id == aquarium_id, Aquarium.owner_user_id == owner_user_id)
            .one_or_none()
        )

    def create(
        self, owner_user_id: str, name: str, aquarium_type: str, volume_liters: float
    ) -> Aquarium:
        self._require_owner(owner_user_id)
        aquarium = Aquarium(
            owner_user_id=owner_user_id,
            name=name,
            type=aquarium_type,
            volume_liters=volume_liters,
        )
        self.session.add(aquarium)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateAquariumNameError("Aquarium name must be unique per user") from exc
        self.session.refresh(aquarium)
        return aquarium

    def update_by_id_and_owner(
        self,
        aquarium_id: str,
        owner_user_id: str,
        updates: dict[str, str | float],
    ) -> Aquarium | None:
        self._require_owner(owner_user_id)
        aquarium = self.get_by_id_and_owner(aquarium_id=aquarium_id, owner_user_id=owner_user_id)
        if aquarium is None:
            return None

        for key, value in updates.items():
            setattr(aquarium, key, value)

        self.session.add(aquarium)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateAquariumNameError("Aquarium name must be unique per user") from exc
        self.session.refresh(aquarium)
        return aquarium

    def delete_by_id_and_owner(self, aquarium_id: str, owner_user_id: str) -> bool:
        self._require_owner(owner_user_id)
        aquarium = self.get_by_id_and_owner(aquarium_id=aquarium_id, owner_user_id=owner_user_id)
        if aquarium is None:
            return False

        self.session.delete(aquarium)
        self.session.commit()
        return True
