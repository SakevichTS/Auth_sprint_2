from pydantic import Field
from pydantic_settings import BaseSettings


class TestSettings(BaseSettings):
    es_host: str = 'http://elasticsearch:9200'
    es_index: str = 'movies'
    #es_id_field: str = ...
    #es_index_mapping: dict = 

    redis_host: str = 'redis'
    redis_port: int = 6379
    service_url: str = 'http://nginx'
 

test_settings = TestSettings() 