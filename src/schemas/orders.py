from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from database.models.orders import OrderStatusEnum
from schemas.movies import MovieListItemSchema


class MessageResponseSchema(BaseModel):
    message: str


class OrderItemResponseSchema(BaseModel):
    id: int
    created_at: datetime
    movie: MovieListItemSchema
    price_at_order: Decimal
    status: OrderStatusEnum

    model_config = ConfigDict(from_attributes=True)


class OrderCreateSchema(BaseModel):
    movie_ids: List[int] = Field(..., min_items=1)


class OrderResponseSchema(BaseModel):
    id: int
    created_at: datetime
    total_amount: Optional[Decimal]
    stripe_url: Optional[str]
    status: OrderStatusEnum
    order_items: List[OrderItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)
