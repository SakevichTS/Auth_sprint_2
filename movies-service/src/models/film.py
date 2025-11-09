
# Используем pydantic для упрощения работы при перегонке данных из json в объекты
from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError
from typing import Optional, List
from uuid import UUID

MAX_WINDOW = 10000

class Film(BaseModel):
    id: str
    title: str

class FilmsQuery(BaseModel):
    sort: Optional[str] = Field(
        default="-imdb_rating",
        description="Поле сортировки, например: '-imdb_rating' или 'title'"
    )
    page_size: int = Field(50, ge=1)
    page_number: int = Field(1, ge=1)
    genre: Optional[str] = Field(
        default=None,
        description="ID жанра для фильтрации"
    )

class FilmShort(BaseModel):
    id: str
    title: str
    imdb_rating: Optional[float] = None

FilmsListResponse = List[FilmShort]

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Строка поиска")
    page_number: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)

    @model_validator(mode="after")
    def check_es_limit(self):
        from_ = (self.page_number - 1) * self.page_size
        if from_ + self.page_size > MAX_WINDOW:
            max_page = (MAX_WINDOW - self.page_size) // self.page_size + 1
            raise PydanticCustomError(
                "es_window_limit",
                f"page_number too large for page_size={self.page_size}; max page is {max_page}",
            )
        return self


class GenreItem(BaseModel):
    id: str
    name: str

class PersonItem(BaseModel):
    id: str
    name: str

class FilmDetail(BaseModel):
    id: str
    title: str
    imdb_rating: Optional[float] = None
    description: Optional[str] = None
    genre: List[GenreItem] = []
    actors: List[PersonItem] = []
    writers: List[PersonItem] = []
    directors: List[PersonItem] = []