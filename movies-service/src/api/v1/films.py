from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from services.film import FilmService, get_film_service
from models.film import FilmDetail, FilmsQuery, FilmsListResponse, SearchQuery

# Объект router, в котором регистрируем обработчики
router = APIRouter()

@router.get("/search", 
            response_model=FilmsListResponse,
            summary="Поиск кинопроизведений",
            description="Полнотекстовый поиск по кинопроизведениям",
            response_description="Название и рейтинг фильма"
            )
async def search_films(params: SearchQuery = Depends(), film_service: FilmService = Depends(get_film_service)) -> FilmsListResponse:
    return await film_service.search(params)
  
@router.get('/{film_id}', 
            response_model=FilmDetail,
            summary="Детальная информация по фильму."
            )
async def film_details(film_id: UUID, film_service: FilmService = Depends(get_film_service)) -> FilmDetail:
    film = await film_service.get_by_id(film_id)
    if not film:
        # Если фильм не найден, отдаём 404 статус
        # Желательно пользоваться уже определёнными HTTP-статусами, которые содержат enum    # Такой код будет более поддерживаемым
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    # Перекладываем данные из models.Film в Film
    # Обратите внимание, что у модели бизнес-логики есть поле description, 
    # которое отсутствует в модели ответа API. 
    # Если бы использовалась общая модель для бизнес-логики и формирования ответов API,
    # вы бы предоставляли клиентам данные, которые им не нужны 
    # и, возможно, данные, которые опасно возвращать
    return film

@router.get("/", 
            response_model=FilmsListResponse,
            summary="Жанр и популярные фильмы в нём.",
            )
async def film_genre(params: FilmsQuery = Depends(), film_service: FilmService = Depends(get_film_service)) -> FilmsListResponse:
    try:
        films = await film_service.list_films(params)
    except Exception:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="failed to fetch films",
        )
    return films

