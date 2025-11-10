import os
import logging
from enum import Enum
from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

class RedisSettings(BaseSettings):
    """Настройки для подключения к Redis."""
    host: str = Field(..., validation_alias='REDIS_HOST')
    port: int = Field(..., validation_alias='REDIS_PORT')

class PostgresSettings(BaseSettings):
    """Настройки для подключения к Postgres."""
    db: str = Field(..., validation_alias='POSTGRES_DB')
    user: str = Field(..., validation_alias='POSTGRES_USER')
    password: str = Field(..., validation_alias='POSTGRES_PASSWORD')
    host: str = Field(..., validation_alias='SQL_HOST')
    port: int = Field(..., validation_alias='SQL_PORT')
    options: str | None = Field(None, validation_alias='SQL_OPTIONS')

    @property
    def async_url(self) -> str:
        """Для FastAPI (async SQLAlchemy)."""
        opts = f"?options={self.options}" if self.options else ""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}{opts}"

class JwtSettings(BaseSettings):
    secret: str = Field(..., validation_alias="JWT_SECRET")
    algorithm: str = "HS256"
    issuer: str = Field("auth-service", validation_alias="JWT_ISS")
    audience: str = Field("movies-service", validation_alias="JWT_AUD")
    access_ttl_min: int = Field(15, validation_alias="ACCESS_TTL_MIN")
    refresh_ttl_days: int = Field(14, validation_alias="REFRESH_TTL_DAYS")

class RateLimitSettings(BaseSettings):
    login_max_attempts: int = Field(5, validation_alias="RL_LOGIN_MAX_ATTEMPTS")
    login_window_sec: int = Field(300, validation_alias="RL_LOGIN_WINDOW_SEC")  # 5 минут
    roles_cache_ttl_sec: int = Field(600, validation_alias="ROLES_CACHE_TTL_SEC")  # 10 минут

class ProjectSettings(BaseSettings):
    """Текстовая информация о проекте"""
    name: str = Field(..., validation_alias='PROJECT_NAME')

class AlchemySettings(BaseSettings):
    """Настройки для Alchemy"""
    echo_engine: bool = Field(False, validation_alias='ECHO_ENGINE')

class AppSettings(BaseSettings):
    """Основной класс с настройками приложения."""
    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        env_file_encoding='utf-8'
    )

    redis: RedisSettings = Field(default_factory=RedisSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    pr: ProjectSettings = Field(default_factory=ProjectSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    ratelimit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    al: AlchemySettings = Field(default_factory=AlchemySettings)


class JaegerSettings(BaseSettings):
    """Настройки Jaeger."""
    host_name: str = Field(..., alias="JAEGER_HOST")
    port: int = Field(..., alias="JAEGER_PORT")
    service_name_auth: str = Field(..., alias="JAEGER_SERVICE_NAME_AUTH")
    endpoint: str = Field(..., alias="JAEGER_ENDPOINT")
    debug: bool = Field(False, alias="JAEGER_DEBUG")

    @property
    def dsn(self) -> str:
        return f"http://{self.host_name}:{self.port}/{self.endpoint}"


try:
    settings = AppSettings()
except Exception as e:
    logging.error(f"Ошибка при загрузке конфигурации: {e}")
    raise

logging_config.dictConfig(LOGGING)

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


   