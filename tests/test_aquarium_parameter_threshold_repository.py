import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.aquarium_parameter_threshold_repository import AquariumParameterThresholdRepository
from src.aquarium_repository import AquariumRepository
from src.db import Base
from src.models import Parameter
from src.user_repository import UserRepository


def _build_repos(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path}/aquarium-parameter-threshold-repo-test.db", future=True
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    return (
        AquariumRepository(session),
        AquariumParameterThresholdRepository(session),
        UserRepository(session),
        session,
    )


def _create_parameter(session, slug: str) -> Parameter:
    parameter = Parameter(slug=slug, display_name=slug.title(), description=None)
    session.add(parameter)
    session.commit()
    session.refresh(parameter)
    return parameter


def test_threshold_repository_create_and_get(tmp_path):
    aquarium_repo, threshold_repo, user_repo, session = _build_repos(tmp_path)
    salinity_parameter = _create_parameter(session, "salinity")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Display",
        aquarium_type="reef",
        volume_liters=120.0,
    )

    assert (
        threshold_repo.get_by_aquarium_and_parameter(aquarium.id, owner.id, salinity_parameter.id)
        is None
    )

    created = threshold_repo.upsert(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=salinity_parameter.id,
        target=35.0,
        min=33.0,
        max=37.0,
        unit="ppt",
    )
    assert created.target == 35.0
    assert created.min == 33.0
    assert created.max == 37.0
    assert created.unit == "ppt"

    fetched = threshold_repo.get_by_aquarium_and_parameter(
        aquarium.id, owner.id, salinity_parameter.id
    )
    assert fetched is not None
    assert fetched.id == created.id


def test_threshold_repository_upsert_replaces_existing_row(tmp_path):
    aquarium_repo, threshold_repo, user_repo, session = _build_repos(tmp_path)
    phosphate_parameter = _create_parameter(session, "phosphate")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-replace")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Nano",
        aquarium_type="reef",
        volume_liters=80.0,
    )

    first = threshold_repo.upsert(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        target=0.05,
        min=None,
        max=0.1,
        unit="ppm",
    )

    second = threshold_repo.upsert(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=phosphate_parameter.id,
        target=0.08,
        min=0.02,
        max=0.12,
        unit="ppm",
    )

    assert second.id == first.id
    assert second.target == 0.08
    assert second.min == 0.02
    assert second.max == 0.12


def test_threshold_repository_unique_per_aquarium_and_parameter(tmp_path):
    aquarium_repo, threshold_repo, user_repo, session = _build_repos(tmp_path)
    salinity_parameter = _create_parameter(session, "salinity")
    temperature_parameter = _create_parameter(session, "temperature")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-unique")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Frag",
        aquarium_type="reef",
        volume_liters=60.0,
    )

    salinity = threshold_repo.upsert(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=salinity_parameter.id,
        target=35.0,
        min=None,
        max=None,
        unit="ppt",
    )
    temperature = threshold_repo.upsert(
        aquarium_id=aquarium.id,
        owner_user_id=owner.id,
        parameter_id=temperature_parameter.id,
        target=25.0,
        min=None,
        max=None,
        unit="celsius",
    )

    assert salinity.id != temperature.id


def test_threshold_repository_rejects_non_owned_aquarium(tmp_path):
    aquarium_repo, threshold_repo, user_repo, session = _build_repos(tmp_path)
    salinity_parameter = _create_parameter(session, "salinity")
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-cross")
    other = user_repo.resolve_or_create("https://issuer.example.com", "other-cross")

    aquarium = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Cross",
        aquarium_type="reef",
        volume_liters=50.0,
    )

    with pytest.raises(ValueError):
        threshold_repo.get_by_aquarium_and_parameter(aquarium.id, other.id, salinity_parameter.id)

    with pytest.raises(ValueError):
        threshold_repo.upsert(
            aquarium_id=aquarium.id,
            owner_user_id=other.id,
            parameter_id=salinity_parameter.id,
            target=35.0,
            min=None,
            max=None,
            unit="ppt",
        )
