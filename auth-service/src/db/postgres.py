from src.core.config import settings

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Создаём движок
# Настройки подключения к БД передаём из переменных окружения, которые заранее загружены в файл настроек
dsn = (
    f"postgresql+asyncpg://{settings.postgres.user}:{settings.postgres.password}"
    f"@{settings.postgres.host}:{settings.postgres.port}/{settings.postgres.db}"
)
engine = create_async_engine(dsn, echo=settings.al.echo_engine, future=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()