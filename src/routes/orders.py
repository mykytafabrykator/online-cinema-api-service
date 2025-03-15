from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import get_db
from database.crud.accounts import get_user_by_id
from database.crud.orders import (
    get_user_orders,
    format_order_detail,
    get_order_by_id,
)
from schemas.orders import OrderItemResponseSchema
from security import JWTAuthManagerInterface
from security.http import get_token

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
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> List[OrderItemResponseSchema]:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

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
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db),
) -> OrderItemResponseSchema:
    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    order = await get_order_by_id(db, order_id, user_id)

    return await format_order_detail(order)
