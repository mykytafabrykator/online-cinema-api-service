from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, User
from database.crud.orders import (
    get_user_orders,
    format_order_detail,
    get_order_by_id,
)
from schemas.orders import OrderItemResponseSchema
from utils import get_current_user

router = APIRouter()


@router.get(
    "/",
    response_model=List[OrderItemResponseSchema],
    summary="Get user's order history",
    responses={
        403: {"description": "Forbidden. You don't have permission."},
        404: {"description": "No orders found."},
        401: {"description": "Unauthorized request."}
    }
)
async def get_user_orders_route(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> List[OrderItemResponseSchema]:
    return await get_user_orders(current_user=user, db=db)


@router.get(
    "/{order_id}/",
    response_model=OrderItemResponseSchema,
    summary="Detail View of an Order",
    responses={
        200: {
            "description": "Order details retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "created_at": "2023-01-01T12:00:00",
                        "movies": [
                            {
                                "id": 1,
                                "name": "Movie A",
                                "year": 2022,
                                "time": 120,
                                "description": "A great movie.",
                            }
                        ],
                        "total_amount": 19.99,
                        "status": "completed",
                    }
                }
            },
        },
        403: {
            "description": (
                "Forbidden. User does not have permission to view this order."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You don't have permission to view "
                                  "this order."
                    }
                }
            },
        },
        404: {
            "description": "Order not found.",
            "content": {
                "application/json": {"example": {"detail": "Order not found."}}
            },
        },
    },
)
async def get_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
) -> OrderItemResponseSchema:
    order = await get_order_by_id(db, order_id, user.id)

    return await format_order_detail(order)
