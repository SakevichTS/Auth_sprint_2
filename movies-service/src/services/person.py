import json
import random

from functools import lru_cache
from typing import Optional, List
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.person import PersonDetail, PersonFilmRole, PersonFilm, PersonSearchItem, PersonSearchFilm
from models.film import SearchQuery

from core.config import settings, Resource

PERSON_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут

class PersonService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, person_id: UUID | str) -> Optional[PersonDetail]:
        pid = str(person_id)
        cache_key = f"person:detail:{pid}"

        if data := await self.redis.get(cache_key):
            return PersonDetail.parse_raw(data)

        try:
            index = settings.es.index_for(Resource.persons)
            doc = await self.elastic.get(index=index, id=pid)
        except NotFoundError:
            return None

        src = doc["_source"]

        films = [
            PersonFilmRole(id=f["id"], roles=f.get("roles", []))
            for f in src.get("films", [])
        ]

        person = PersonDetail(
            id=src.get("id"),
            full_name=src.get("full_name", ""),
            films=films,
        )

        await self.redis.set(cache_key, person.json(), ex=PERSON_CACHE_EXPIRE_IN_SECONDS)
        return person
    
    async def get_person_films(self, person_id: UUID | str) -> List[PersonFilm]:
        pid = str(person_id)
        cache_key = f"person:films:{pid}"

        # 1. Пробуем достать из кеша
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [PersonFilm(**item) for item in data]

        # 2. Берём документ персоны из ES
        try:
            index = settings.es.index_for(Resource.persons)
            doc = await self.elastic.get(index=index, id=pid)
        except NotFoundError:
            await self.redis.set(cache_key, "[]", ex=PERSON_CACHE_EXPIRE_IN_SECONDS)
            return []

        source = doc.get("_source", {})
        films_data = source.get("films", [])

        # 3. Собираем id фильмов
        film_ids: List[str] = []
        for item in films_data:
            fid = item.get("id")
            if fid:
                film_ids.append(fid)

        if not film_ids:
            await self.redis.set(cache_key, "[]", ex=PERSON_CACHE_EXPIRE_IN_SECONDS)
            return []

        # 4. mget фильмов
        index = settings.es.index_for(Resource.films)
        resp = await self.elastic.mget(index=index, body={"ids": film_ids})

        result: List[PersonFilm] = []
        for d in resp.get("docs", []):
            if not d.get("found"):
                continue
            src = d.get("_source", {})
            result.append(
                PersonFilm(
                    id=src.get("id"),
                    title=src.get("title", ""),
                    imdb_rating=src.get("imdb_rating"),
                )
            )

        # 5. Сохраняем в кеш
        await self.redis.set(
            cache_key,
            json.dumps([film.dict() for film in result]),
            ex=PERSON_CACHE_EXPIRE_IN_SECONDS,
        )
        return result
    
    async def search(self, params: SearchQuery) -> List[PersonSearchItem]:
        cache_key = f"persons:search:{params.query}:{params.page_number}:{params.page_size}"

        # 1) пробуем из кеша
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [PersonSearchItem(**item) for item in data]

        from_ = (params.page_number - 1) * params.page_size

        es_query = {
            "match": {
                "full_name": {
                    "query": params.query,
                    "operator": "and"
                }
            }
        }

        index = settings.es.index_for(Resource.persons)
        resp = await self.elastic.search(
            index=index,
            query=es_query,
            from_=from_,
            size=params.page_size,
        )

        hits = resp.get("hits", {}).get("hits", [])
        items: List[PersonSearchItem] = []

        for h in hits:
            src = h.get("_source", {}) or {}
            pid = src.get("id")
            full_name = src.get("full_name")
            if not pid or not full_name:
                continue

            films = []
            for f in src.get("films", []) or []:
                fid = f.get("id")
                if not fid:
                    continue
                films.append(PersonSearchFilm(id=fid, roles=f.get("roles", [])))

            items.append(PersonSearchItem(id=pid, full_name=full_name, films=films))

        # --- 3) кладём в кэш ---
        if self.redis:
            payload = json.dumps([i.model_dump(mode="json") for i in items])
            await self.redis.set(cache_key, payload, ex=PERSON_CACHE_EXPIRE_IN_SECONDS+random.randint(0, 5))

        return items

@lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    return PersonService(redis, elastic)