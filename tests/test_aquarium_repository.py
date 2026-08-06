import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from conftest import register_engine_for_cleanup
from src.aquarium_repository import AquariumRepository, DuplicateAquariumNameError
from src.db import Base
from src.user_repository import UserRepository


def _build_repos(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/aquarium-repo-test.db", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    register_engine_for_cleanup(session, engine)
    return AquariumRepository(session), UserRepository(session), session


def test_aquarium_repository_crud_and_owner_scoping(tmp_path):
    aquarium_repo, user_repo, _ = _build_repos(tmp_path)
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner")
    other = user_repo.resolve_or_create("https://issuer.example.com", "other")

    created = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Main Reef",
        aquarium_type="reef",
        volume_liters=250.0,
    )

    owner_list = aquarium_repo.list_by_owner(owner.id)
    other_list = aquarium_repo.list_by_owner(other.id)

    assert len(owner_list) == 1
    assert owner_list[0].id == created.id
    assert other_list == []

    owner_fetch = aquarium_repo.get_by_id_and_owner(created.id, owner.id)
    other_fetch = aquarium_repo.get_by_id_and_owner(created.id, other.id)
    assert owner_fetch is not None
    assert other_fetch is None

    updated = aquarium_repo.update_by_id_and_owner(
        aquarium_id=created.id,
        owner_user_id=owner.id,
        updates={"name": "Main Reef Updated", "type": "mixed", "volume_liters": 300.0},
    )
    assert updated is not None
    assert updated.name == "Main Reef Updated"
    assert updated.type == "mixed"
    assert updated.volume_liters == 300.0

    wrong_owner_update = aquarium_repo.update_by_id_and_owner(
        aquarium_id=created.id,
        owner_user_id=other.id,
        updates={"name": "Nope"},
    )
    assert wrong_owner_update is None

    assert aquarium_repo.delete_by_id_and_owner(created.id, other.id) is False
    assert aquarium_repo.delete_by_id_and_owner(created.id, owner.id) is True


def test_aquarium_name_uniqueness_per_user(tmp_path):
    aquarium_repo, user_repo, _ = _build_repos(tmp_path)
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-a")
    other = user_repo.resolve_or_create("https://issuer.example.com", "owner-b")

    aquarium_repo.create(
        owner_user_id=owner.id,
        name="Nano",
        aquarium_type="reef",
        volume_liters=80.0,
    )

    with pytest.raises(DuplicateAquariumNameError):
        aquarium_repo.create(
            owner_user_id=owner.id,
            name="Nano",
            aquarium_type="reef",
            volume_liters=85.0,
        )

    # Same name is allowed for different users.
    other_created = aquarium_repo.create(
        owner_user_id=other.id,
        name="Nano",
        aquarium_type="reef",
        volume_liters=90.0,
    )
    assert other_created.id


def test_aquarium_name_uniqueness_on_update(tmp_path):
    aquarium_repo, user_repo, _ = _build_repos(tmp_path)
    owner = user_repo.resolve_or_create("https://issuer.example.com", "owner-c")

    first = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Display",
        aquarium_type="reef",
        volume_liters=300.0,
    )
    second = aquarium_repo.create(
        owner_user_id=owner.id,
        name="Frag",
        aquarium_type="reef",
        volume_liters=120.0,
    )

    with pytest.raises(DuplicateAquariumNameError):
        aquarium_repo.update_by_id_and_owner(
            aquarium_id=second.id,
            owner_user_id=owner.id,
            updates={"name": first.name},
        )


def test_owner_id_is_required_for_queries(tmp_path):
    aquarium_repo, _, _ = _build_repos(tmp_path)

    for call in (
        lambda: aquarium_repo.list_by_owner(""),
        lambda: aquarium_repo.get_by_id_and_owner("aq", ""),
        lambda: aquarium_repo.create("", "A", "reef", 10.0),
        lambda: aquarium_repo.update_by_id_and_owner("aq", "", {}),
        lambda: aquarium_repo.delete_by_id_and_owner("aq", ""),
    ):
        with pytest.raises(ValueError):
            call()
