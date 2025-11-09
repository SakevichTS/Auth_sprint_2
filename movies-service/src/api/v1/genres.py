from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from services.genre import GenreService, get_genre_service
from models.genre import GenresListResponse, Genre

router = APIRouter()

@router.get(
        "/", 
        response_model=GenresListResponse, 
        summary="Список жанров"
)
async def list_genres(genre_service: GenreService = Depends(get_genre_service)) -> GenresListResponse:
    return await genre_service.list()

@router.get(
        "/{genre_id}", 
        response_model=Genre, 
        summary="Данные по конкретному жанру"
)
async def genre_details(
    genre_id: UUID,
    genre_service: GenreService = Depends(get_genre_service)
) -> Genre:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="genre not found")
    return genre