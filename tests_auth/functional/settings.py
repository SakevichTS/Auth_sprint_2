from pydantic import Field
from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    redis_host: str = 'redis'
    redis_port: int = 6379
    service_url: str = 'http://nginx'
    # Postgres
    pg_host: str = "auth-db"
    pg_port: int = 5432
    pg_db: str = "auth"
    pg_user: str = "app"
    pg_password: str = "secret"
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    #admin
    admin_login: str = "admin"
    admin_password: str = "secret"
    admin_email: str = "admin@example.com"
 

test_settings = TestSettings() 