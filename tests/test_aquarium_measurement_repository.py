from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.aquarium_measurement_repository import (
    AquariumMeasurementRepository,
    DuplicateAquariumMeasurementError,
)
from src.aquarium_repository import AquariumRepository
from src.db import Base
from src.models import Parameter, Unit
from src.user_repository import UserRepository


def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _build_repos(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path}/aquarium-measurement-repo-test.db", future=True
    )
    event.listen(engine, "connect", _enable_foreign_keys)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    return (
        AquariumRepository(session),
        AquariumMeasurementRepository(session),
        UserRepository(session),
        session,
    )


def _create_parameter(session, slug: str) -> Parameter:
    parameter = Parameter(slug=slug, display_name=slug.title(), description=None)
    session.add(parameter)
    session.commit()
    session.refresh(parameter)
    return parameter


def _create_unit(session, slug: str) -> Unit:
    existing = session.query(Unit).filter(Unit.slug == slug).one_or_none()
    if existing is not None:
        return existing
    unit = Unit(slug=slug, display_name=slug, description=None)
    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit


def test_measurement_repository_create_list_and_filters(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    _create_parameter(session, "salinity")
    _create_unit(session, "ppt")
    _create_unit(session, "sg")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner")
    other = user_repo.resolve_or_create("https://issuer.example.com", "other")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Display",
        aquarium_type="reef",
        volume_liters=120.0,
    )

    m1 = measurement_repo.create_salinity(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        value_ppt=34.8,
        raw_value=1.026,
        raw_unit="sg",
        measured_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    m2 = measurement_repo.create_salinity(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        value_ppt=35.0,
        raw_value=35.0,
        raw_unit="ppt",
        measured_at=datetime(2026, 7, 1, 12, 5, 0, tzinfo=timezone.utc),
    )

    all_rows = measurement_repo.list_salinity(aquarium.id, owner.id)
    assert [m.id for m in all_rows] == [m1.id, m2.id]
    assert all_rows[0].raw_value == 1.026
    assert all_rows[0].raw_unit.slug == "sg"
    assert all_rows[1].unit.slug == "ppt"

    filtered_rows = measurement_repo.list_salinity(
        aquarium.id,
        owner.id,
        measured_from=datetime(2026, 7, 1, 12, 1, 0, tzinfo=timezone.utc),
    )
    assert [m.id for m in filtered_rows] == [m2.id]

    with pytest.raises(ValueError):
        measurement_repo.list_salinity(aquarium.id, other.id)


def test_measurement_repository_rejects_duplicate_timestamp(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    _create_parameter(session, "salinity")
    _create_unit(session, "ppt")
    _create_unit(session, "sg")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner")
    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Nano",
        aquarium_type="reef",
        volume_liters=80.0,
    )
    measured_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

    measurement_repo.create_salinity(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        value_ppt=35.0,
        raw_value=35.0,
        raw_unit="ppt",
        measured_at=measured_at,
    )

    with pytest.raises(DuplicateAquariumMeasurementError):
        measurement_repo.create_salinity(
            aquarium_id=aquarium.id,
            owner_user_id=owner.id,
            value_ppt=35.1,
            raw_value=1.026,
            raw_unit="sg",
            measured_at=measured_at,
        )


def test_measurement_repository_generic_create_and_filtering(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    salinity_parameter = _create_parameter(session, "salinity")
    phosphate_parameter = _create_parameter(session, "phosphate")
    ppt_unit = _create_unit(session, "ppt")
    ppm_unit = _create_unit(session, "ppm")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-generic")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Frag Tank",
        aquarium_type="reef",
        volume_liters=90.0,
    )

    salinity = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=salinity_parameter.id,
        value=35.0,
        unit_id=ppt_unit.id,
        raw_value=35.0,
        raw_unit_id=ppt_unit.id,
        measured_at=datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc),
    )
    phosphate = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        value=0.08,
        unit_id=ppm_unit.id,
        raw_value=0.08,
        raw_unit_id=ppm_unit.id,
        measured_at=datetime(2026, 7, 2, 12, 5, 0, tzinfo=timezone.utc),
    )

    all_rows = measurement_repo.list_measurements(aquarium.id, owner.id)
    assert [m.id for m in all_rows] == [salinity.id, phosphate.id]

    phosphate_rows = measurement_repo.list_measurements(
        aquarium.id,
        owner.id,
        parameter_id=phosphate_parameter.id,
    )
    assert [m.id for m in phosphate_rows] == [phosphate.id]


def test_measurement_repository_rejects_duplicate_phosphate_timestamp(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    phosphate_parameter = _create_parameter(session, "phosphate")
    ppm_unit = _create_unit(session, "ppm")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-phosphate")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Phosphate Tank",
        aquarium_type="reef",
        volume_liters=70.0,
    )
    measured_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)

    measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        value=0.09,
        unit_id=ppm_unit.id,
        raw_value=0.09,
        raw_unit_id=ppm_unit.id,
        measured_at=measured_at,
    )

    with pytest.raises(DuplicateAquariumMeasurementError):
        measurement_repo.create_measurement(
            aquarium_id=aquarium.id,
            owner_user_id=owner.id,
            parameter_id=phosphate_parameter.id,
            value=0.10,
            unit_id=ppm_unit.id,
            raw_value=0.10,
            raw_unit_id=ppm_unit.id,
            measured_at=measured_at,
        )


def test_measurement_repository_delete_by_id_and_parameter(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    phosphate_parameter = _create_parameter(session, "phosphate")
    ppm_unit = _create_unit(session, "ppm")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-delete")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Delete Tank",
        aquarium_type="reef",
        volume_liters=95.0,
    )

    created = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        value=0.08,
        unit_id=ppm_unit.id,
        raw_value=0.08,
        raw_unit_id=ppm_unit.id,
        measured_at=datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert measurement_repo.delete_measurement(
        aquarium_id=aquarium.id,
        parameter_id=phosphate_parameter.id,
        measurement_id=created.id,
    )

    assert not measurement_repo.delete_measurement(
        aquarium_id=aquarium.id,
        parameter_id=phosphate_parameter.id,
        measurement_id=created.id,
    )


def test_measurement_repository_unit_fk_restricts_deletion_while_referenced(tmp_path):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    phosphate_parameter = _create_parameter(session, "phosphate")
    ppm_unit = _create_unit(session, "ppm")
    unused_unit = _create_unit(session, "unused")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-unit-fk")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Unit FK Tank",
        aquarium_type="reef",
        volume_liters=60.0,
    )

    measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        value=0.08,
        unit_id=ppm_unit.id,
        raw_value=0.08,
        raw_unit_id=ppm_unit.id,
        measured_at=datetime(2026, 7, 5, 9, 0, 0, tzinfo=timezone.utc),
    )

    session.delete(unused_unit)
    session.commit()

    session.delete(ppm_unit)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize(
    ("parameter", "value", "unit"),
    [
        ("calcium", 420.0, "ppm"),
        ("ammonia", 0.25, "mg/L"),
        ("nitrite", 0.5, "ppm"),
        ("nitrate", 10.0, "ppm"),
        ("ph", 8.2, "pH"),
        ("alkalinity", 9.5, "dKH"),
        ("magnesium", 1300.0, "ppm"),
    ],
)
def test_measurement_repository_persists_new_parameters(tmp_path, parameter, value, unit):
    aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)
    parameter_row = _create_parameter(session, parameter)
    unit_row = _create_unit(session, unit)
    owner = user_repo.resolve_or_create("https://issuer.example.com", f"owner-{parameter}")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name=f"{parameter.title()} Tank",
        aquarium_type="reef",
        volume_liters=100.0,
    )
    measured_at = datetime(2026, 7, 4, 9, 0, 0, tzinfo=timezone.utc)

    created = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=parameter_row.id,
        value=value,
        unit_id=unit_row.id,
        raw_value=value,
        raw_unit_id=unit_row.id,
        measured_at=measured_at,
    )

    rows = measurement_repo.list_measurements(aquarium.id, owner.id, parameter_id=parameter_row.id)
    assert [row.id for row in rows] == [created.id]
    assert rows[0].value == value
    assert rows[0].unit.slug == unit

    with pytest.raises(DuplicateAquariumMeasurementError):
        measurement_repo.create_measurement(
            aquarium_id=aquarium.id,
            owner_user_id=owner.id,
            parameter_id=parameter_row.id,
            value=value,
            unit_id=unit_row.id,
            raw_value=value,
            raw_unit_id=unit_row.id,
            measured_at=measured_at,
        )
