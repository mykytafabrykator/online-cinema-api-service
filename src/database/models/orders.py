from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, func, String
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, User, Movie, Payment, PaymentItem


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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        SQLAlchemyEnum(OrderStatusEnum), nullable=False, default="PENDING"
    )
    total_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2))
    stripe_url: Mapped[str | None] = mapped_column(String)

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order"
    )
    user: Mapped["User"] = relationship("User", back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )


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
    price_at_order: Mapped[float] = mapped_column(
        DECIMAL(10, 2),
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="order_items"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="order_items"
    )
    payment_items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="order_item",
        cascade="all, delete-orphan"
    )
