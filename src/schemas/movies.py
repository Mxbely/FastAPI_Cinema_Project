from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class GenresSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class StarsSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class DirectorsSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    time: int
    description: str

    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = ConfigDict(from_attributes=True)


class MovieBaseSchema(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)
    description: str
    price: float = Field(..., ge=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value):
        first_movie_year = 1888
        current_year = datetime.now().year
        if value < first_movie_year or value > current_year:
            raise ValueError(f"Year must be between {first_movie_year} and {current_year}.")


class MovieDetailSchema(MovieBaseSchema):
    id: int
    certification: CertificationSchema
    genres: List[GenresSchema]
    stars: List[StarsSchema]
    directors: List[DirectorsSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieFilter(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    min_imdb: Optional[float] = None
    max_imdb: Optional[float] = None
    min_votes: Optional[int] = None
    max_votes: Optional[int] = None
    genre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
