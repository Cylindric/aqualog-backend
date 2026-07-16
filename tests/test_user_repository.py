from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aqualog_api.db import Base
from aqualog_api.user_repository import UserRepository


def _build_repo(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/repo-test.db", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
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


def test_update_profile_changes_allowed_fields(tmp_path):
    repo, _ = _build_repo(tmp_path)
    user = repo.resolve_or_create("https://issuer.example.com", "sub-2")

    updated = repo.update_profile(user, {"display_name": "Coral Keeper", "bio": "Mixed reef"})

    assert updated.display_name == "Coral Keeper"
    assert updated.bio == "Mixed reef"
