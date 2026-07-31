from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Aquarium, AquariumParameterThreshold


class AquariumParameterThresholdRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_aquarium_and_parameter(
        self, aquarium_id: uuid.UUID, owner_user_id: uuid.UUID, parameter_id: uuid.UUID
    ) -> AquariumParameterThreshold | None:
        if not self._is_owned_aquarium(aquarium_id, owner_user_id):
            raise ValueError("Aquarium not found")

        return (
            self.session.query(AquariumParameterThreshold)
            .filter(
                AquariumParameterThreshold.aquarium_id == aquarium_id,
                AquariumParameterThreshold.parameter_id == parameter_id,
            )
            .one_or_none()
        )

    def upsert(
        self,
        aquarium_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        parameter_id: uuid.UUID,
        target: float | None,
        min: float | None,
        max: float | None,
        unit: str,
    ) -> AquariumParameterThreshold:
        if not self._is_owned_aquarium(aquarium_id, owner_user_id):
            raise ValueError("Aquarium not found")

        threshold = (
            self.session.query(AquariumParameterThreshold)
            .filter(
                AquariumParameterThreshold.aquarium_id == aquarium_id,
                AquariumParameterThreshold.parameter_id == parameter_id,
            )
            .one_or_none()
        )
        if threshold is None:
            threshold = AquariumParameterThreshold(
                aquarium_id=aquarium_id,
                parameter_id=parameter_id,
            )
            self.session.add(threshold)

        threshold.target = target
        threshold.min = min
        threshold.max = max
        threshold.unit = unit

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

        self.session.refresh(threshold)
        return threshold

    def _is_owned_aquarium(self, aquarium_id: uuid.UUID, owner_user_id: uuid.UUID) -> bool:
        return (
            self.session.query(Aquarium.id)
            .filter(Aquarium.id == aquarium_id, Aquarium.owner_user_id == owner_user_id)
            .first()
            is not None
        )
