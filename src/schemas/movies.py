import enum
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.accounts import UserRegistrationResponseSchema


class CertificationSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class CertificationResponseSchema(CertificationSchema):
    id: int


class GenresSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class GenreResponseSchema(GenresSchema):
    id: int


class StarsSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

class StarsResponseSchema(StarsSchema):
    id: int

class DirectorsSchema(BaseModel):
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
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)
    description: str
    price: float = Field(..., ge=0)


    model_config = ConfigDict(from_attributes=True)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        first_movie_year = 1888
        current_year = datetime.now().year
        if value < first_movie_year or value > current_year:
            raise ValueError(
                f"Year must be between {first_movie_year} and {current_year}."
            )
        return value


class MovieCreateSchema(MovieBaseSchema):
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)
    certification: str
    genres: list[str]
    stars: list[str]
    directors: list[str]


class MovieDetailSchema(MovieBaseSchema):
    id: int
    uuid: str
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)
    certification: CertificationResponseSchema
    genres: List[GenresSchema]
    stars: List[StarsSchema]
    directors: List[DirectorsSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    year: Optional[int]
    time: Optional[int] = Field(None, ge=0)
    imdb: Optional[float] = Field(None, ge=0, le=10)
    votes: Optional[int] = Field(None, ge=0)
    description: Optional[str]
    price: Optional[float] = Field(None, ge=0)
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[float] = Field(None, ge=0)


class MovieLikeResponseSchema(BaseModel):
    # user_id: int = Field(None, ge=0)
    # movie_id: int = Field(None, ge=0)
    is_liked: bool
    created_at: datetime
    user: UserRegistrationResponseSchema
    movie: MovieListItemSchema

    class Config:
        from_attributes = True


class MovieFavoriteResponseSchema(BaseModel):
    # user_id: int = Field(None, ge=0)
    # movie_id: int = Field(None, ge=0)
    is_favorited: bool
    created_at: datetime
    user: UserRegistrationResponseSchema
    movie: MovieListItemSchema

    class Config:
        from_attributes = True


class MovieSortEnum(str, enum.Enum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    RELEASE_YEAR_ASC = "release_year_asc"
    RELEASE_YEAR_DESC = "release_year_desc"
    VOTES_ASC = "votes_asc"
    VOTES_DESC = "votes_desc"
    IMDb_ASC = "imdb_asc"
    IMDb_DESC = "imdb_desc"

class DetailMessageSchema(BaseModel):
    detail: str
