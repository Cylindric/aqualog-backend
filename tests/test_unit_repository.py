from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.aquarium_measurement_repository import AquariumMeasurementRepository
from src.aquarium_repository import AquariumRepository
from src.db import Base
from src.models import Parameter, ParameterUnit
from src.unit_repository import DuplicateUnitSlugError, UnitInUseError, UnitRepository
from src.user_repository import UserRepository


def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _build_repos(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/unit-repo-test.db", future=True)
    event.listen(engine, "connect", _enable_foreign_keys)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    return (
        UnitRepository(session),
        AquariumRepository(session),
        AquariumMeasurementRepository(session),
        UserRepository(session),
        session,
    )


def test_unit_repository_crud(tmp_path):
    unit_repo, _, _, _, _ = _build_repos(tmp_path)

    assert unit_repo.get_by_slug("iron-unit") is None

    created = unit_repo.create(
        slug="mol/L", display_name="Moles per Litre", description="Molar concentration."
    )
    assert created.slug == "mol/L"
    assert created.display_name == "Moles per Litre"

    fetched = unit_repo.get_by_slug("mol/L")
    assert fetched is not None
    assert fetched.id == created.id

    all_units = unit_repo.list_all()
    assert [u.slug for u in all_units] == ["mol/L"]

    updated = unit_repo.update_by_slug(
        "mol/L", {"display_name": "mol/L (updated)", "description": "Updated description."}
    )
    assert updated is not None
    assert updated.display_name == "mol/L (updated)"
    assert updated.description == "Updated description."

    assert unit_repo.delete_by_slug("mol/L") is True
    assert unit_repo.get_by_slug("mol/L") is None


def test_unit_repository_get_by_slug_is_case_insensitive(tmp_path):
    unit_repo, _, _, _, _ = _build_repos(tmp_path)

    unit_repo.create(slug="pH", display_name="pH", description=None)

    assert unit_repo.get_by_slug("ph") is not None
    assert unit_repo.get_by_slug("PH") is not None
    assert unit_repo.get_by_slug("Ph") is not None


def test_unit_repository_duplicate_slug_is_rejected_case_insensitively(tmp_path):
    unit_repo, _, _, _, _ = _build_repos(tmp_path)

    unit_repo.create(slug="pH", display_name="pH", description=None)

    with pytest.raises(DuplicateUnitSlugError):
        unit_repo.create(slug="PH", display_name="pH again", description=None)


def test_unit_repository_update_and_delete_missing_slug_are_no_ops(tmp_path):
    unit_repo, _, _, _, _ = _build_repos(tmp_path)

    assert unit_repo.update_by_slug("missing", {"display_name": "X"}) is None
    assert unit_repo.delete_by_slug("missing") is False


def test_unit_repository_delete_blocked_while_referenced_by_measurement(tmp_path):
    unit_repo, aquarium_repo, measurement_repo, user_repo, session = _build_repos(tmp_path)

    ppt_unit = unit_repo.create(slug="ppt", display_name="Parts per Thousand", description=None)
    salinity_parameter = Parameter(slug="salinity", display_name="Salinity", description=None)
    session.add(salinity_parameter)
    session.commit()
    session.refresh(salinity_parameter)

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
        unit_id=ppt_unit.id,
        raw_value=35.0,
        raw_unit_id=ppt_unit.id,
        measured_at=datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(UnitInUseError):
        unit_repo.delete_by_slug("ppt")

    measurement_repo.delete_measurement(
        aquarium_id=aquarium.id, parameter_id=salinity_parameter.id, measurement_id=measurement.id
    )

    assert unit_repo.delete_by_slug("ppt") is True


def test_unit_repository_delete_blocked_while_referenced_by_parameter_unit(tmp_path):
    unit_repo, _, _, _, session = _build_repos(tmp_path)

    ppt_unit = unit_repo.create(slug="ppt", display_name="Parts per Thousand", description=None)
    salinity_parameter = Parameter(slug="salinity", display_name="Salinity", description=None)
    session.add(salinity_parameter)
    session.commit()
    session.refresh(salinity_parameter)

    session.add(
        ParameterUnit(parameter_id=salinity_parameter.id, unit_id=ppt_unit.id, is_canonical=True)
    )
    session.commit()

    with pytest.raises(UnitInUseError):
        unit_repo.delete_by_slug("ppt")


def test_unit_repository_list_units_and_canonical_unit_for_parameter(tmp_path):
    unit_repo, _, _, _, session = _build_repos(tmp_path)

    ppt_unit = unit_repo.create(slug="ppt", display_name="Parts per Thousand", description=None)
    sg_unit = unit_repo.create(slug="sg", display_name="Specific Gravity", description=None)
    salinity_parameter = Parameter(slug="salinity", display_name="Salinity", description=None)
    session.add(salinity_parameter)
    session.commit()
    session.refresh(salinity_parameter)

    session.add_all(
        [
            ParameterUnit(
                parameter_id=salinity_parameter.id, unit_id=ppt_unit.id, is_canonical=True
            ),
            ParameterUnit(
                parameter_id=salinity_parameter.id, unit_id=sg_unit.id, is_canonical=False
            ),
        ]
    )
    session.commit()

    units = unit_repo.list_units_for_parameter(salinity_parameter.id)
    assert {u.slug for u in units} == {"ppt", "sg"}

    canonical = unit_repo.get_canonical_unit(salinity_parameter.id)
    assert canonical is not None
    assert canonical.slug == "ppt"

    assert unit_repo.is_unit_valid_for_parameter(salinity_parameter.id, ppt_unit.id) is True
    assert unit_repo.is_unit_valid_for_parameter(salinity_parameter.id, sg_unit.id) is True

    other_unit = unit_repo.create(slug="celsius", display_name="Celsius", description=None)
    assert unit_repo.is_unit_valid_for_parameter(salinity_parameter.id, other_unit.id) is False
