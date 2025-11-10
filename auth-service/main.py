from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse, JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from redis.asyncio import Redis
from contextlib import asynccontextmanager

from src.api.v1 import auth, roles
from src.core.config import settings
from src.core.jaeger import configure_tracer, jaeger_settings
from src.core.ratelimit import check_login_ratelimit
from src.db import redis

from pydantic import ValidationError


# новый подход запуска и завершения , 
# код до yeild выполняется для старта, 
# после yeild - для завершения и освобожждления ресурсов
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis.redis = Redis(host=settings.redis.host, port=settings.redis.port)
    yield
    await redis.redis.close()

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
    description="AUTH API для онлайн кинотеатра",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def login_ratelimit_middleware(request: Request, call_next):
    # Простейший вариант: проверяем только путь /auth/login
    if request.url.path == "/auth/login" and request.method == "POST":
        form = await request.form()
        login = form.get("username")
        ip = request.client.host
        # Проверяем лимит
        await check_login_ratelimit(ip, login)

    response = await call_next(request)
    return response


# Обработчик  ошибок Pydantic
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    # Логика для обработки стандартных ошибок валидации Pydantic
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(roles.router, prefix="/roles", tags=["roles"])

# if jaeger_settings.debug:
#     configure_tracer()
#     FastAPIInstrumentor.instrument_app(app)

