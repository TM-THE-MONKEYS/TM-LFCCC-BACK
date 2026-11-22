from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.logging import logger
from app.core.security import hash_password, verify_password
from app.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import PasswordChangeInput, PasswordResetInput, UserPatchInput


class UserService:
    """User administration (admin) and self-service password change."""

    def __init__(self, db: Session) -> None:
        self._repo = UserRepository(db)
        self._db = db

    def get_by_id(self, user_id: str) -> User:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"Usuário com id '{user_id}' não encontrado.")
        return user

    def patch(self, user_id: str, data: UserPatchInput, *, actor: User) -> User:
        user = self.get_by_id(user_id)
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        if "role" in updates:
            updates["role"] = UserRole(updates["role"]).value

        if self._removes_active_admin(user, updates):
            if user.id == actor.id:
                raise ConflictError("Você não pode desativar nem rebaixar a própria conta.")
            if len(self._repo.lock_active_admin_ids()) <= 1:
                raise ConflictError(
                    "Não é possível desativar ou rebaixar o último administrador ativo."
                )

        for field, value in updates.items():
            setattr(user, field, value)
        self._repo.update(user)
        logger.info(
            "user_updated actor_id=%s user_id=%s fields=%s",
            actor.id,
            user.id,
            sorted(updates),
        )
        return user

    def reset_password(self, user_id: str, data: PasswordResetInput, *, actor: User) -> User:
        user = self.get_by_id(user_id)
        if user.id == actor.id:
            raise ConflictError(
                "Para alterar a própria senha use POST /users/me/password informando a atual."
            )
        user.password_hash = hash_password(data.new_password)
        self._repo.update(user)
        logger.info("user_password_reset actor_id=%s user_id=%s", actor.id, user.id)
        return user

    def change_own_password(self, user: User, data: PasswordChangeInput) -> User:
        if not verify_password(data.current_password, user.password_hash):
            logger.info("user_password_change outcome=wrong_current user_id=%s", user.id)
            raise UnprocessableError("Senha atual incorreta.")
        if data.new_password == data.current_password:
            raise UnprocessableError("A nova senha deve ser diferente da atual.")
        user.password_hash = hash_password(data.new_password)
        self._repo.update(user)
        logger.info("user_password_change outcome=success user_id=%s", user.id)
        return user

    @staticmethod
    def _removes_active_admin(user: User, updates: dict[str, object]) -> bool:
        if user.role != UserRole.admin.value or not user.is_active:
            return False
        demoted = updates.get("role", user.role) != UserRole.admin.value
        deactivated = updates.get("is_active", True) is False
        return demoted or deactivated
