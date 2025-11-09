from pydantic import BaseModel, Field
from typing import Optional, List

class PersonFilmRole(BaseModel):
    id: str
    roles: List[str] = Field(default_factory=list)

class PersonDetail(BaseModel):
    id: str
    full_name: str
    films: List[PersonFilmRole] = Field(default_factory=list)

class PersonFilm(BaseModel):
    id: str
    title: str
    imdb_rating: Optional[float] = None

class PersonSearchFilm(BaseModel):
    id: str
    roles: List[str] = Field(default_factory=list)

class PersonSearchItem(BaseModel):
    id: str
    full_name: str
    films: List[PersonSearchFilm] = Field(default_factory=list)

PersonsSearchResponse = List[PersonSearchItem]