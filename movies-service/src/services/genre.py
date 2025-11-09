from functools import lru_cache
from typing import List, Dict, Any, Optional
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis

from models.genre import Genre

from core.config import settings, Resource


GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут

class GenreService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic
        
    async def get_by_id(self, genre_id: UUID | str) -> Optional[Genre]:
        gid = str(genre_id)
        cache_key = f"genre:{gid}"

        # 1) cache hit
        if cached := await self.redis.get(cache_key):
            return Genre.parse_raw(cached)

        # 2) из ES
        try:
            index = settings.es.index_for(Resource.genres)
            doc = await self.elastic.get(index=index, id=gid)
        except NotFoundError:
            return None

        src = doc["_source"]
        genre = Genre(
            id=src.get("id"),
            name=src.get("name"),
        )

        # 3) сохранить в кеш
        await self.redis.set(cache_key, genre.json(), ex=GENRE_CACHE_EXPIRE_IN_SECONDS)
        return genre
    
    async def list(self) -> List[Genre]:
        cache_key = "genres:all"

        # 1) пробуем из кэша
        if cached := await self.redis.get(cache_key):
            import json
            return [Genre(**item) for item in json.loads(cached)]

        # 2) берём все жанры из ES
        index = settings.es.index_for(Resource.genres)
        resp = await self.elastic.search(
            index=index,
            query={"match_all": {}},
            size=1000,  # если жанров немного
        )

        hits = resp.get("hits", {}).get("hits", [])
        items: List[Genre] = []
        for h in hits:
            src = h.get("_source", {}) or {}
            gid = src.get("id")
            name = src.get("name")
            if not gid or not name:
                continue
            items.append(Genre(id=gid, name=name))

        # 3) сохраним в кэш
        import json
        await self.redis.set(cache_key, json.dumps([g.dict() for g in items]), ex=GENRE_CACHE_EXPIRE_IN_SECONDS)

        return items

@lru_cache()
def get_genre_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic)