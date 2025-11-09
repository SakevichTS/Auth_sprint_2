from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse, JSONResponse
from redis.asyncio import Redis
from contextlib import asynccontextmanager

from api.v1 import films, persons, genres
from core.config import settings
from db import elastic, redis

from pydantic import ValidationError

# новый подход запуска и завершения , 
# код до yeild выполняется для старта, 
# после yeild - для завершения и освобожждления ресурсов
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis.redis = Redis(host=settings.redis.host, port=settings.redis.port)
    elastic.es = AsyncElasticsearch(hosts=[f'{settings.es.protocol}://{settings.es.host}:{settings.es.port}'])
    yield
    await redis.redis.close()
    await elastic.es.close()

app = FastAPI(
    # Конфигурируем название проекта. Оно будет отображаться в документации
    title=settings.pr.name,
    # Адрес документации в красивом интерфейсе
    docs_url='/api/openapi',
    # Адрес документации в формате OpenAPI
    openapi_url='/api/openapi.json',
    # Можно сразу сделать небольшую оптимизацию сервиса 
    # и заменить стандартный JSON-сериализатор на более шуструю версию, написанную на Rust
    default_response_class=ORJSONResponse,
    description="Информация о фильмах, жанрах и людях, участвовавших в создании произведения",
    version="1.0.0",
    lifespan=lifespan
)

# Обработчик  ошибок Pydantic
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    # Логика для обработки стандартных ошибок валидации Pydantic
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

app.include_router(films.router, prefix='/api/v1/films', tags=['films'])
app.include_router(persons.router, prefix='/api/v1/persons', tags=['person'])
app.include_router(genres.router, prefix='/api/v1/genres', tags=['genre'])