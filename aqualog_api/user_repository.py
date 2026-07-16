from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aqualog_api.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_identity(self, oauth_issuer: str, oauth_subject: str) -> User | None:
        return (
            self.session.query(User)
            .filter(User.oauth_issuer == oauth_issuer, User.oauth_subject == oauth_subject)
            .one_or_none()
        )

    def create_for_identity(self, oauth_issuer: str, oauth_subject: str) -> User:
        user = User(oauth_issuer=oauth_issuer, oauth_subject=oauth_subject)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def resolve_or_create(self, oauth_issuer: str, oauth_subject: str) -> User:
        existing = self.get_by_identity(oauth_issuer=oauth_issuer, oauth_subject=oauth_subject)
        if existing is not None:
            return existing

        try:
            return self.create_for_identity(oauth_issuer=oauth_issuer, oauth_subject=oauth_subject)
        except IntegrityError:
            self.session.rollback()
            # Another request may have created this mapping concurrently.
            existing = self.get_by_identity(oauth_issuer=oauth_issuer, oauth_subject=oauth_subject)
            if existing is None:
                raise
            return existing

    def update_profile(self, user: User, updates: dict[str, str | None]) -> User:
        for key, value in updates.items():
            setattr(user, key, value)

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
