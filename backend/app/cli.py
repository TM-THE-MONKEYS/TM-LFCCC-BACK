"""CLI administrativa — criação de usuários sem registro público.

Uso (a partir de backend/):
    python -m app.cli create-admin --email admin@vitrine.local --password 'SenhaForte123!'
    python -m app.cli create-user --name Operador --email op@vitrine.local --password 'SenhaForte123!'
    python -m app.cli create-user --name Admin2 --email a2@vitrine.local --password '...' --role admin
"""

from __future__ import annotations

import argparse
import getpass
import sys
import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _prompt_password() -> str:
    password = getpass.getpass("Senha: ")
    confirm = getpass.getpass("Confirmar senha: ")
    if password != confirm:
        print("Erro: senhas não conferem.", file=sys.stderr)
        sys.exit(1)
    return password


def _create_user(
    *,
    name: str,
    email: str,
    password: str | None,
    role: UserRole,
) -> None:
    email_norm = email.strip().lower()
    pwd = password or _prompt_password()
    if len(pwd) < 8:
        print("Erro: a senha deve ter no mínimo 8 caracteres.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.get_by_email(email_norm) is not None:
            print(f"Erro: já existe um usuário com o e-mail '{email_norm}'.", file=sys.stderr)
            sys.exit(1)
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email_norm,
            password_hash=hash_password(pwd),
            role=role.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        repo.create(user)
        db.commit()
        print(f"Usuário criado: {email_norm} (role={role.value})")
    finally:
        db.close()


def cmd_create_admin(args: argparse.Namespace) -> None:
    email = args.email or settings.ADMIN_EMAIL
    password = args.password
    if password is None and settings.is_production:
        # Never silently reuse ADMIN_PASSWORD default in production — always prompt.
        password = None
    elif password is None and not sys.stdin.isatty():
        password = settings.admin_password_value
    _create_user(
        name=args.name or "Admin",
        email=email,
        password=password,
        role=UserRole.admin,
    )


def cmd_create_user(args: argparse.Namespace) -> None:
    role = UserRole(args.role)
    _create_user(
        name=args.name,
        email=args.email,
        password=args.password,
        role=role,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="CLI Vitrine")
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="Cria um usuário admin")
    admin.add_argument("--email", default=None, help="E-mail (default: ADMIN_EMAIL)")
    admin.add_argument("--name", default="Admin", help="Nome de exibição")
    admin.add_argument("--password", default=None, help="Senha (prompt se omitida)")
    admin.set_defaults(func=cmd_create_admin)

    user = sub.add_parser("create-user", help="Cria um usuário (operator ou admin)")
    user.add_argument("--name", required=True)
    user.add_argument("--email", required=True)
    user.add_argument("--password", default=None, help="Senha (prompt se omitida)")
    user.add_argument(
        "--role",
        default=UserRole.operator.value,
        choices=[r.value for r in UserRole],
    )
    user.set_defaults(func=cmd_create_user)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
