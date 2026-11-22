from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.scalar(select(User).where(User.id == user_id))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.strip().lower()))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(User)) or 0)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def lock_active_admin_ids(self) -> list[str]:
        """Active admin ids, row-locked (FOR UPDATE) until the transaction ends.

        Serializes concurrent demotions so two admins cannot remove each other at once.
        Aggregates are not allowed with FOR UPDATE, hence ids instead of COUNT.
        """
        stmt = (
            select(User.id)
            .where(User.role == UserRole.admin.value, User.is_active.is_(True))
            .with_for_update()
        )
        return list(self.db.scalars(stmt).all())

    def update(self, user: User) -> User:
        self.db.flush()
        return user
