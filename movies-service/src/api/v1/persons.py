from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from services.person import PersonService, get_person_service
from models.person import PersonDetail, PersonFilm, PersonsSearchResponse
from models.film import SearchQuery

# Объект router, в котором регистрируем обработчики
router = APIRouter()

@router.get(
        "/search", 
        response_model=PersonsSearchResponse,
        summary="Поиск персоны"
)
async def search_persons(
    params: SearchQuery = Depends(),
    person_service: PersonService = Depends(get_person_service),
):
    return await person_service.search(params)

@router.get(
    "/{person_id}",
    response_model=PersonDetail,
    summary="Детальная карточка персоны"
)
async def person_details(
    person_id: UUID,
    person_service: PersonService = Depends(get_person_service),
) -> PersonDetail:
    person = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")
    return person

@router.get(
    "/{person_id}/film",
    response_model=List[PersonFilm],
    summary="Фильмы персоны",
    description="Возвращает список фильмов с id, title и imdb_rating."
)
async def person_films(
    person_id: UUID,
    person_service: PersonService = Depends(get_person_service)
) -> list[PersonFilm]:
    films = await person_service.get_person_films(str(person_id))
    return films
