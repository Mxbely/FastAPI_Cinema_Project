from datetime import datetime
from sqlalchemy import (
    ForeignKey,
    Integer,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from database.models.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cart(user_id={self.user_id})>"


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    movie: Mapped["Movie"] = relationship("Movie")

    __table_args__ = (
        UniqueConstraint("cart_id", "movie_id", name="unique_cart_movie_constraint"),
    )

    def __repr__(self):
        return f"<CartItem(cart_id={self.cart_id}, movie_id={self.movie_id}, added_at={self.added_at})>"