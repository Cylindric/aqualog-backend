from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.aquarium_measurement_repository import (
    AquariumMeasurementRepository,
    DuplicateAquariumMeasurementError,
)
from src.aquarium_repository import AquariumRepository
from src.db import Base
from src.user_repository import UserRepository


def _build_repos(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/aquarium-measurement-repo-test.db", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    return AquariumRepository(session), AquariumMeasurementRepository(session), UserRepository(session), session


def test_measurement_repository_create_list_and_filters(tmp_path):
    aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)
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
    assert all_rows[0].raw_unit == "sg"
    assert all_rows[1].unit == "ppt"

    filtered_rows = measurement_repo.list_salinity(
        aquarium.id,
        owner.id,
        measured_from=datetime(2026, 7, 1, 12, 1, 0, tzinfo=timezone.utc),
    )
    assert [m.id for m in filtered_rows] == [m2.id]

    try:
        measurement_repo.list_salinity(aquarium.id, other.id)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_measurement_repository_rejects_duplicate_timestamp(tmp_path):
    aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)
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

    try:
        measurement_repo.create_salinity(
            aquarium_id=aquarium.id,
            owner_user_id=owner.id,
            value_ppt=35.1,
            raw_value=1.026,
            raw_unit="sg",
            measured_at=measured_at,
        )
        assert False, "Expected DuplicateAquariumMeasurementError"
    except DuplicateAquariumMeasurementError:
        pass


def test_measurement_repository_generic_create_and_filtering(tmp_path):
    aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)
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
        parameter="salinity",
        value=35.0,
        unit="ppt",
        raw_value=35.0,
        raw_unit="ppt",
        measured_at=datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc),
    )
    phosphate = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter="phosphate",
        value=0.08,
        unit="ppm",
        raw_value=0.08,
        raw_unit="ppm",
        measured_at=datetime(2026, 7, 2, 12, 5, 0, tzinfo=timezone.utc),
    )

    all_rows = measurement_repo.list_measurements(aquarium.id, owner.id)
    assert [m.id for m in all_rows] == [salinity.id, phosphate.id]

    phosphate_rows = measurement_repo.list_measurements(
        aquarium.id,
        owner.id,
        parameter="phosphate",
    )
    assert [m.id for m in phosphate_rows] == [phosphate.id]


def test_measurement_repository_rejects_duplicate_phosphate_timestamp(tmp_path):
    aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)
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
        parameter="phosphate",
        value=0.09,
        unit="ppm",
        raw_value=0.09,
        raw_unit="ppm",
        measured_at=measured_at,
    )

    try:
        measurement_repo.create_measurement(
            aquarium_id=aquarium.id,
            owner_user_id=owner.id,
            parameter="phosphate",
            value=0.10,
            unit="ppm",
            raw_value=0.10,
            raw_unit="ppm",
            measured_at=measured_at,
        )
        assert False, "Expected DuplicateAquariumMeasurementError"
    except DuplicateAquariumMeasurementError:
        pass


def test_measurement_repository_delete_by_id_and_parameter(tmp_path):
    aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)
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
        parameter="phosphate",
        value=0.08,
        unit="ppm",
        raw_value=0.08,
        raw_unit="ppm",
        measured_at=datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert measurement_repo.delete_measurement(
        aquarium_id=aquarium.id,
        parameter="phosphate",
        measurement_id=created.id,
    )

    assert not measurement_repo.delete_measurement(
        aquarium_id=aquarium.id,
        parameter="phosphate",
        measurement_id=created.id,
    )
