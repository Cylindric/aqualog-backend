from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.aquarium_measurement_repository import AquariumMeasurementRepository
from src.aquarium_repository import AquariumRepository
from src.db import Base
from src.parameter_repository import (
    DuplicateParameterSlugError,
    ParameterInUseError,
    ParameterRepository,
)
from src.user_repository import UserRepository


def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _build_repos(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/parameter-repo-test.db", future=True)
    event.listen(engine, "connect", _enable_foreign_keys)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    return (
        ParameterRepository(session),
        AquariumRepository(session),
        AquariumMeasurementRepository(session),
        UserRepository(session),
        session,
    )


def test_parameter_repository_crud(tmp_path):
    parameter_repo, _, _, _, _ = _build_repos(tmp_path)

    assert parameter_repo.get_by_slug("iron") is None

    created = parameter_repo.create(
        slug="iron", display_name="Iron", description="Trace element for planted tanks."
    )
    assert created.slug == "iron"
    assert created.display_name == "Iron"

    fetched = parameter_repo.get_by_slug("iron")
    assert fetched is not None
    assert fetched.id == created.id

    all_parameters = parameter_repo.list_all()
    assert [p.slug for p in all_parameters] == ["iron"]

    updated = parameter_repo.update_by_slug(
        "iron", {"display_name": "Iron (Fe)", "description": "Updated description."}
    )
    assert updated is not None
    assert updated.display_name == "Iron (Fe)"
    assert updated.description == "Updated description."

    assert parameter_repo.delete_by_slug("iron") is True
    assert parameter_repo.get_by_slug("iron") is None


def test_parameter_repository_duplicate_slug_is_rejected(tmp_path):
    parameter_repo, _, _, _, _ = _build_repos(tmp_path)

    parameter_repo.create(slug="salinity", display_name="Salinity", description=None)

    with pytest.raises(DuplicateParameterSlugError):
        parameter_repo.create(slug="salinity", display_name="Salinity Again", description=None)


def test_parameter_repository_update_and_delete_missing_slug_are_no_ops(tmp_path):
    parameter_repo, _, _, _, _ = _build_repos(tmp_path)

    assert parameter_repo.update_by_slug("missing", {"display_name": "X"}) is None
    assert parameter_repo.delete_by_slug("missing") is False


def test_parameter_repository_delete_blocked_while_referenced_by_measurement(tmp_path):
    parameter_repo, aquarium_repo, measurement_repo, user_repo, _ = _build_repos(tmp_path)

    salinity_parameter = parameter_repo.create(
        slug="salinity", display_name="Salinity", description=None
    )
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner")
    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Display",
        aquarium_type="reef",
        volume_liters=100.0,
    )
    measurement = measurement_repo.create_measurement(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=salinity_parameter.id,
        value=35.0,
        unit="ppt",
        raw_value=35.0,
        raw_unit="ppt",
        measured_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ParameterInUseError):
        parameter_repo.delete_by_slug("salinity")

    measurement_repo.delete_measurement(
        aquarium_id=aquarium.id, parameter_id=salinity_parameter.id, measurement_id=measurement.id
    )

    assert parameter_repo.delete_by_slug("salinity") is True
