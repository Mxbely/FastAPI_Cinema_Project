from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    Boolean,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class MovieGenres(Base):
    __tablename__ = "movie_genres"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class MovieDirectors(Base):
    __tablename__ = "movie_directors"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    director_id: Mapped[int] = mapped_column(
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True
    )


class MovieStars(Base):
    __tablename__ = "movie_stars"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    star_id: Mapped[int] = mapped_column(
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary="movie_genres", back_populates="genres"
    )

    def __repr__(self) -> str:
        return f"<Genre (name='{self.name}')>"


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary="movie_stars", back_populates="stars"
    )

    def __repr__(self) -> str:
        return f"<Star (name='{self.name}')>"


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", secondary="movie_directors", back_populates="directors"
    )

    def __repr__(self) -> str:
        return f"<Director (name='{self.name}')>"


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", back_populates="certification"
    )

    def __repr__(self) -> str:
        return f"<Certification (name='{self.name}')>"


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id"), nullable=False
    )
    certification: Mapped["Certification"] = relationship(
        "Certification", back_populates="movies"
    )

    genres: Mapped[list["Genre"]] = relationship(
        "Genre", secondary="movie_genres", back_populates="movies"
    )

    stars: Mapped[list["Star"]] = relationship(
        "Star", secondary="movie_stars", back_populates="movies"
    )

    directors: Mapped[list["Director"]] = relationship(
        "Director", secondary="movie_directors", back_populates="movies"
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="movie"
    )
    likes: Mapped[list["MovieLike"]] = relationship(
        "MovieLike", back_populates="movie", cascade="all, delete-orphan"
    )

    favorites: Mapped[list["FavoriteMovie"]] = relationship(
        "FavoriteMovie", back_populates="movie", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_constraint"),
    )

    def __repr__(self) -> str:
        return f"<Movie (name='{self.name}', imdb='{self.imdb}', time='{self.time}')>"



class MovieLike(Base):
    __tablename__ = "movie_likes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    is_liked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="likes")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="likes")

    def __repr__(self) -> str:
        return (
            f"<MovieLike (user_id='{self.user_id}', "
            f"movie_id='{self.movie_id}', "
            f"is_liked='{self.is_liked}')>"
        )


class FavoriteMovie(Base):
    __tablename__ = "favorite_movies"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    is_favorited: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="favorites")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="favorites")

    def __repr__(self) -> str:
        return f"<FavoriteMovie (user_id='{self.user_id}', movie_id='{self.movie_id}')>"
