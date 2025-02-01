from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, DECIMAL, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        String(50), nullable=False, default=OrderStatusEnum.PENDING.value
    )
    total_amount: Mapped[float | None] = mapped_column(DECIMAL(10, 2))

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order"
    )
    user: Mapped["User"] = relationship("User", back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="order_items")
    payment_items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem", back_populates="order_item", cascade="all, delete-orphan"
    )