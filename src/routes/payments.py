from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import PaymentStatusEnum, get_db
from database.crud.accounts import get_user_by_id
from database.crud.payments import get_user_payments
from schemas import PaymentHistoryResponse
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface

router = APIRouter()


@router.get(
    "/",
    response_model=list[PaymentHistoryResponse],
    summary="Get list of user's payments",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "amount": 100.0,
                            "status": "PENDING",
                            "created_at": "2023-01-01T00:00:00"
                        }
                    ]
                }
            }
        },
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    },
)
async def read_payments(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> list[PaymentHistoryResponse]:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    payments = await get_user_payments(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        payment_status=payment_status
    )

    return payments
