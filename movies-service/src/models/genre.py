from pydantic import BaseModel
from typing import List, Optional

class Genre(BaseModel):
    id: str
    name: str

GenresListResponse = List[Genre]