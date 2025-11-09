import asyncio
import typer
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.postgres import async_session
from src.domain.repositories.user_repo import UserRepository
from src.domain.repositories.role_repo import RoleRepository
from src.core.security import hash_password
from src.models.orm.user import User

app = typer.Typer(help="Management commands")

@app.command("create-admin")
def create_admin(
    login: str = typer.Option(..., help="Login"),
    email: str = typer.Option(..., help="Email"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    first_name: str = typer.Option("", help="First name"),
    last_name: str = typer.Option("", help="Last name"),
):
    """Создать пользователя с ролью admin."""
    asyncio.run(_create_admin(login, email, password, first_name, last_name))

async def _create_admin(login: str, email: str, password: str, first_name: str, last_name: str):
    user_repo = UserRepository()
    role_repo = RoleRepository()

    async with async_session() as db:
        # Проверим, есть ли уже роль admin
        role = await role_repo.get_by_name(db, "admin")
        if not role:
            role = await role_repo.create(db, "admin", "Administrator role")

        # Проверим, есть ли уже пользователь
        user = await user_repo.get_by_login(db, login)
        if user:
            typer.echo(f"⚠️ Пользователь '{login}' уже существует.")
            if role not in user.roles:
                user.roles.append(role)
                await db.commit()
                typer.echo("✅ Роль 'admin' добавлена существующему пользователю.")
            return

        # Создаём нового пользователя
        user = User(
            login=login,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=hash_password(password),
        )
        user.roles.append(role)
        db.add(user)
        await db.commit()
        typer.secho(f"✅ Создан администратор: {user.login}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()