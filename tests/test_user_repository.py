import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from conftest import register_engine_for_cleanup
from src.db import Base
from src.user_repository import UserRepository


def _build_repo(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/repo-test.db", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    register_engine_for_cleanup(session, engine)
    return UserRepository(session), session


def test_resolve_or_create_reuses_existing_identity(tmp_path):
    repo, session = _build_repo(tmp_path)

    user1 = repo.resolve_or_create("https://issuer.example.com", "sub-1")
    user2 = repo.resolve_or_create("https://issuer.example.com", "sub-1")

    assert user1.id == user2.id
    assert (
        session.query(type(user1))
        .filter_by(oauth_issuer="https://issuer.example.com", oauth_subject="sub-1")
        .count()
        == 1
    )


def test_get_by_identity_returns_none_when_unknown(tmp_path):
    repo, _ = _build_repo(tmp_path)

    result = repo.get_by_identity("https://issuer.example.com", "unknown")

    assert result is None


def test_get_by_id_returns_existing_user(tmp_path):
    repo, _ = _build_repo(tmp_path)
    created = repo.resolve_or_create("https://issuer.example.com", "sub-get-by-id")

    result = repo.get_by_id(str(created.id))

    assert result is not None
    assert result.id == created.id


def test_get_by_id_returns_none_when_unknown(tmp_path):
    repo, _ = _build_repo(tmp_path)

    result = repo.get_by_id(str(uuid.uuid4()))

    assert result is None


def test_get_by_id_returns_none_for_malformed_id(tmp_path):
    repo, _ = _build_repo(tmp_path)

    result = repo.get_by_id("not-a-uuid")

    assert result is None


def test_update_profile_changes_allowed_fields(tmp_path):
    repo, _ = _build_repo(tmp_path)
    user = repo.resolve_or_create("https://issuer.example.com", "sub-2")

    updated = repo.update_profile(user, {"display_name": "Coral Keeper", "bio": "Mixed reef"})

    assert updated.display_name == "Coral Keeper"
    assert updated.bio == "Mixed reef"


def test_resolve_or_create_captures_username_on_creation(tmp_path):
    repo, _ = _build_repo(tmp_path)

    user = repo.resolve_or_create("https://issuer.example.com", "sub-3", username="coral-keeper")

    assert user.username == "coral-keeper"


def test_resolve_or_create_allows_null_username(tmp_path):
    repo, _ = _build_repo(tmp_path)

    user = repo.resolve_or_create("https://issuer.example.com", "sub-4")

    assert user.username is None


def test_resolve_or_create_does_not_overwrite_username_on_repeat_login(tmp_path):
    repo, _ = _build_repo(tmp_path)

    first = repo.resolve_or_create("https://issuer.example.com", "sub-5", username="original-name")
    second = repo.resolve_or_create("https://issuer.example.com", "sub-5", username="changed-name")

    assert first.id == second.id
    assert second.username == "original-name"
