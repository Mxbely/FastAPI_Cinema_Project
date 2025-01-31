from typing import Optional
from uuid import uuid4, UUID


from database.models.base import Base
from sqlalchemy import (
    String,
    Text,
    DECIMAL,
    ForeignKey,
    Float,
    UniqueConstraint,
    Table,
    Column
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)


MovieGenres = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)

MovieDirectors = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)

MovieStars = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movie_genres: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MovieGenres,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre (name='{self.name}')>"


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movie_stars: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MovieStars,
        back_populates="stars"
    )

    def __repr__(self):
        return f"<Star (name='{self.name}')>"


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movie_directors: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MovieDirectors,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director (name='{self.name}')>"


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movie: Mapped[list["Movie"]] = relationship(
        "Movie",
        back_populates="certification"
    )

    def __repr__(self):
        return f"<Certification (name='{self.name}')>"


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)
    certification: Mapped["Certification"] = relationship(
        "Certification",
        back_populates="movies"
    )

    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=MovieGenres,
        back_populates="movies"
    )

    stars: Mapped[list["Star"]] = relationship(
        "Star",
        secondary=MovieStars,
        back_populates="movies"
    )

    directors: Mapped[list["Director"]] = relationship(
        "Director",
        secondary=MovieDirectors,
        back_populates="movies"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_constraint")
    )

    def __repr__(self):
        return f"<Movie (name='{self.name}', imdb='{self.imdb}', time='{self.time}')>"
