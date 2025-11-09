import os
import logging
from enum import Enum
from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING

class Resource(str, Enum):
    films = "films"
    genres = "genres"
    persons = "persons"

class ElasticsearchSettings(BaseSettings):
    host: str = Field(..., validation_alias="ELASTIC_HOST")
    port: int = Field(..., validation_alias="ELASTIC_PORT")
    protocol: str = Field(..., validation_alias="ELASTIC_SCHEMA")

    films_index: str = Field(..., validation_alias="ES_FILMS_INDEX")
    genres_index: str = Field(..., validation_alias="ES_GENRES_INDEX")
    persons_index: str = Field(..., validation_alias="ES_PERSONS_INDEX")

    def index_for(self, resource: Resource) -> str:
        mapping = {
            Resource.films: self.films_index,
            Resource.genres: self.genres_index,
            Resource.persons: self.persons_index,
        }
        return mapping[resource]

class RedisSettings(BaseSettings):
    """Настройки для подключения к Redis."""
    host: str = Field(..., validation_alias='REDIS_HOST')
    port: int = Field(..., validation_alias='REDIS_PORT')

class ProjectSettings(BaseSettings):
    """Текстовая информация о проекте"""
    name: str = Field(..., validation_alias='PROJECT_NAME')

class AppSettings(BaseSettings):
    """Основной класс с настройками приложения."""
    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        env_file_encoding='utf-8'
    )

    redis: RedisSettings = Field(default_factory=RedisSettings)
    es: ElasticsearchSettings = Field(default_factory=ElasticsearchSettings)
    pr: ProjectSettings = Field(default_factory=ProjectSettings)

try:
    settings = AppSettings()
except Exception as e:
    logging.error(f"Ошибка при загрузке конфигурации: {e}")
    raise

logging_config.dictConfig(LOGGING)

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


   