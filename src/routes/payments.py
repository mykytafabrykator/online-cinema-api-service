from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from database import PaymentStatusEnum, get_db, User
from database.crud.payments import get_user_payments
from schemas import PaymentHistoryResponse
from utils import get_current_user

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
    user: User = Depends(get_current_user)
) -> list[PaymentHistoryResponse]:
    payments = await get_user_payments(
        db=db,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        payment_status=payment_status
    )

    return payments
