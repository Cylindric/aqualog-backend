from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Aquarium, AquariumMeasurement, Parameter


class DuplicateAquariumMeasurementError(ValueError):
    pass


class AquariumMeasurementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_salinity(
        self,
        aquarium_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        value_ppt: float,
        raw_value: float,
        raw_unit: str,
        measured_at: datetime,
    ) -> AquariumMeasurement:
        return self.create_measurement(
            aquarium_id=aquarium_id,
            owner_user_id=owner_user_id,
            parameter_id=self._salinity_parameter_id(),
            value=value_ppt,
            unit="ppt",
            raw_value=raw_value,
            raw_unit=raw_unit,
            measured_at=measured_at,
        )

    def create_measurement(
        self,
        aquarium_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        parameter_id: uuid.UUID,
        value: float,
        unit: str,
        raw_value: float,
        raw_unit: str,
        measured_at: datetime,
    ) -> AquariumMeasurement:
        measurement = AquariumMeasurement(
            aquarium_id=aquarium_id,
            parameter_id=parameter_id,
            value=value,
            unit=unit,
            raw_value=raw_value,
            raw_unit=raw_unit,
            measured_at=measured_at,
        )
        if not self._is_owned_aquarium(aquarium_id, owner_user_id):
            raise ValueError("Aquarium not found")

        self.session.add(measurement)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateAquariumMeasurementError("Duplicate salinity reading timestamp") from exc

        self.session.refresh(measurement)
        return measurement

    def list_salinity(
        self,
        aquarium_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        measured_from: datetime | None = None,
        measured_to: datetime | None = None,
    ) -> list[AquariumMeasurement]:
        return self.list_measurements(
            aquarium_id=aquarium_id,
            owner_user_id=owner_user_id,
            measured_from=measured_from,
            measured_to=measured_to,
            parameter_id=self._salinity_parameter_id(),
        )

    def list_measurements(
        self,
        aquarium_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        measured_from: datetime | None = None,
        measured_to: datetime | None = None,
        parameter_id: uuid.UUID | None = None,
    ) -> list[AquariumMeasurement]:
        if not self._is_owned_aquarium(aquarium_id, owner_user_id):
            raise ValueError("Aquarium not found")

        query = self.session.query(AquariumMeasurement).filter(
            AquariumMeasurement.aquarium_id == aquarium_id
        )

        if parameter_id is not None:
            query = query.filter(AquariumMeasurement.parameter_id == parameter_id)

        if measured_from is not None:
            query = query.filter(AquariumMeasurement.measured_at >= measured_from)
        if measured_to is not None:
            query = query.filter(AquariumMeasurement.measured_at <= measured_to)

        return query.order_by(AquariumMeasurement.measured_at.asc()).all()

    def delete_measurement(
        self,
        aquarium_id: uuid.UUID,
        parameter_id: uuid.UUID,
        measurement_id: uuid.UUID,
    ) -> bool:
        measurement = (
            self.session.query(AquariumMeasurement)
            .filter(
                AquariumMeasurement.id == measurement_id,
                AquariumMeasurement.aquarium_id == aquarium_id,
                AquariumMeasurement.parameter_id == parameter_id,
            )
            .first()
        )
        if measurement is None:
            return False

        self.session.delete(measurement)
        self.session.commit()
        return True

    def _is_owned_aquarium(self, aquarium_id: uuid.UUID, owner_user_id: uuid.UUID) -> bool:
        return (
            self.session.query(Aquarium.id)
            .filter(Aquarium.id == aquarium_id, Aquarium.owner_user_id == owner_user_id)
            .first()
            is not None
        )

    def _salinity_parameter_id(self) -> uuid.UUID:
        return self.session.query(Parameter.id).filter(Parameter.slug == "salinity").one()[0]
