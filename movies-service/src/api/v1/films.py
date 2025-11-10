from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.film import FilmService, get_film_service
from models.film import FilmDetail, FilmsQuery, FilmsListResponse, SearchQuery
from auth_service.dependencies import get_current_user
from auth_service.http_client import UserPayload


# Объект router, в котором регистрируем обработчики
router = APIRouter()


@router.get(
    "/search",
    response_model=FilmsListResponse,
    summary="Поиск кинопроизведений",
    description="Полнотекстовый поиск по кинопроизведениям",
    response_description="Название и рейтинг фильма",
)
async def search_films(
    params: SearchQuery = Depends(),
    film_service: FilmService = Depends(get_film_service),
    user: UserPayload = Depends(get_current_user),
) -> FilmsListResponse:
    return await film_service.search(params)


@router.get(
    "/{film_id}",
    response_model=FilmDetail,
    summary="Детальная информация по фильму.",
)
async def film_details(
    film_id: UUID,
    film_service: FilmService = Depends(get_film_service),
    user: UserPayload = Depends(get_current_user),
) -> FilmDetail:
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")
    return film


@router.get(
    "/",
    response_model=FilmsListResponse,
    summary="Жанр и популярные фильмы в нём.",
)
async def film_genre(
    params: FilmsQuery = Depends(),
    film_service: FilmService = Depends(get_film_service),
    user: UserPayload = Depends(get_current_user),
) -> FilmsListResponse:
    try:
        films = await film_service.list_films(params)
    except Exception:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="failed to fetch films",
        )
    return films