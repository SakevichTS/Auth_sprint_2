import json
import random

from functools import lru_cache
from typing import List, Dict, Any, Optional, Sequence
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import FilmsQuery, FilmShort, FilmsListResponse, SearchQuery, FilmDetail

from core.config import settings, Resource

from abc import ABC, abstractmethod


FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут

class AbstractCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...


class AbstractDataStorage(ABC):
    @abstractmethod
    async def get_by_id(self, film_id: UUID | str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    async def list_films(
        self, sort: Optional[str], page_number: int, page_size: int, genre: Optional[str] = None
    ) -> Sequence[Dict[str, Any]]:
        ...

    @abstractmethod
    async def search(
        self, query: str,page_number: int, page_size: int,
    ) -> Sequence[Dict[str, Any]]:
        ...


class ElasticDataStorage(AbstractDataStorage):
    def __init__(self, es: AsyncElasticsearch):
        self._es = es
        self._index = settings.es.index_for(Resource.films)

    async def get_by_id(self, film_id: UUID | str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self._es.get(index=self._index, id=str(film_id))
        except NotFoundError:
            return None
        return doc["_source"]

    async def list_films(
        self, sort: Optional[str], page_number: int, page_size: int, genre: Optional[str] = None
    ) -> Sequence[Dict[str, Any]]:
        from_ = (page_number - 1) * page_size
        es_sort = self._es_sort_from_query(sort)
        es_query = self._build_films_query_nested_genre(genre)

        resp = await self._es.search(
            index=self._index,
            query=es_query,
            sort=es_sort,
            from_=from_,
            size=page_size,
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    def _build_films_query_nested_genre(self, genre_id: Optional[str]) -> Dict[str, Any]:
        if not genre_id:
            return {"match_all": {}}
        return {
            "term": {"genre.id": genre_id}
        }

    def _es_sort_from_query(self, sort: Optional[str]) -> list[Dict[str, Any]]:
        if not sort:
            return [{"imdb_rating": {"order": "desc", "unmapped_type": "keyword"}}]
        field = sort.lstrip("-")
        order = "desc" if sort.startswith("-") else "asc"
        return [{field: {"order": order, "unmapped_type": "keyword"}}]

    async def search(
        self, query: str, page_number: int, page_size: int,
    ) -> Sequence[Dict[str, Any]]:
        from_ = (page_number - 1) * page_size
        es_query = {
            "match": {
                "title": {
                    "query": query,
                    "operator": "and",
                }
            }
        }
        resp = await self._es.search(
            index=self._index,
            query=es_query,
            from_=from_,
            size=page_size,
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]


class RedisCache(AbstractCache):
    def __init__(self, client: Redis):
        self._client = client

    async def get(self, key: str) -> Optional[str]:
        # Пытаемся получить данные о фильме из кеша, используя команду get
        # https://redis.io/commands/get/
        val = await self._client.get(key)
        if val is None:
            return None
        # redis возвращает bytes → приводим к str
        return val.decode() if isinstance(val, (bytes, bytearray)) else val

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        # Сохраняем данные о фильме, используя команду set
        # Выставляем время жизни кеша — 5 минут
        # https://redis.io/commands/set/
        # pydantic позволяет сериализовать модель в json
        if ttl:
            await self._client.set(key, value, ex=ttl)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)


# FilmService содержит бизнес-логику по работе с фильмами. 
# Никакой магии тут нет. Обычный класс с обычными методами. 
# Этот класс ничего не знает про DI — максимально сильный и независимый.
class FilmService:
    def __init__(self, cache: AbstractCache, storage: AbstractDataStorage):
        self.cache = cache
        self.storage = storage

    async def list_films(self, params: FilmsQuery) -> FilmsListResponse:
        cache_key = f"films:{params.sort}:{params.page_number}:{params.page_size}:{params.genre or 'any'}"

        # 1) кэш
        if cached := await self.cache.get(cache_key):
            data = json.loads(cached)
            return [FilmShort(**item) for item in data]

        # 2) ES через storage (распаковываем поля из params)
        docs = await self.storage.list_films(
            sort=params.sort,
            page_number=params.page_number,
            page_size=params.page_size,
            genre=params.genre,
        )

        items: List[FilmShort] = []
        for src in docs:
            es_id = src.get("id")
            title = src.get("title")
            rating = src.get("imdb_rating")
            if not es_id or not title:
                continue
            items.append(FilmShort(id=es_id, title=title, imdb_rating=rating))

        # 3) сохранить в кэш
        if items:
            await self.cache.set(
                cache_key,
                json.dumps([i.dict() for i in items]),
                ttl=FILM_CACHE_EXPIRE_IN_SECONDS,
            )

        return items
       
    async def search(self, params: SearchQuery) -> FilmsListResponse:
        cache_key = f"films:search:{params.query}:{params.page_number}:{params.page_size}"

        # 1) кэш
        cached = await self.cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [FilmShort(**item) for item in data]

        # 2) storage (ES)
        docs = await self.storage.search(
            query=params.query,
            page_number=params.page_number,
            page_size=params.page_size,
        )

        items: List[FilmShort] = []
        for src in docs:
            es_id = src.get("id")
            title = src.get("title")
            rating = src.get("imdb_rating")
            if not es_id or not title:
                continue
            items.append(FilmShort(id=es_id, title=title, imdb_rating=rating))

        # 3) кэшируем c небольшим «джиттером»
        if items:
            payload = json.dumps([i.dict() for i in items])
            await self.cache.set(
                cache_key,
                payload,
                ttl=FILM_CACHE_EXPIRE_IN_SECONDS + random.randint(0, 5),
            )

        return items

    async def get_by_id(self, film_id: UUID | str) -> Optional[FilmDetail]:
        fid = str(film_id)
        cache_key = f"film:{fid}"

        # 1) кэш
        raw = await self.cache.get(cache_key)
        if raw:
            return FilmDetail.parse_raw(raw)

        # 2) основное хранилище (Elastic через абстракцию)
        doc = await self.storage.get_by_id(fid)  # dict | None
        if not doc:
            return None
        film = FilmDetail(**doc)

        # 3) положить в кэш и вернуть
        await self.cache.set(cache_key, film.model_dump_json(), ttl=FILM_CACHE_EXPIRE_IN_SECONDS)

        return film


@lru_cache()
def get_film_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    cache: AbstractCache = RedisCache(redis)
    storage: AbstractDataStorage = ElasticDataStorage(elastic)
    return FilmService(cache=cache, storage=storage)
