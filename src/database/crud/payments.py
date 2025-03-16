import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from database import Order, Payment, PaymentItem, PaymentStatusEnum
from schemas import PaymentCreateSchema, PaymentHistoryResponse


async def create_payment(
        payment_data: PaymentCreateSchema,
        db: AsyncSession
) -> Payment:
    try:
        payment = Payment(
            user_id=payment_data.user_id,
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            external_payment_id=payment_data.external_payment_id,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return payment
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )


async def create_payment_items(
    payment: Payment, order: Order, db: AsyncSession
) -> list[PaymentItem]:
    payment_items = []
    try:
        for order_item in order.order_items:
            payment_item = PaymentItem(
                payment_id=payment.id,
                order_item_id=order_item.id,
                price_at_payment=order_item.price_at_order,
            )
            payment_items.append(payment_item)

        db.add_all(payment_items)
        await db.commit()
        return payment_items
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment items: {str(e)}"
        )


async def update_payment_status(
        payment: Payment,
        new_status: PaymentStatusEnum,
        db: AsyncSession,
) -> Payment:
    try:
        payment.status = new_status
        await db.commit()
        await db.refresh(payment)
        return payment
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment status: {str(e)}"
        )


async def get_payment_by_session_id(
        session_id: str,
        db: AsyncSession
) -> Optional[Payment]:
    try:
        result = await db.execute(
            select(Payment).filter_by(external_payment_id=session_id)
        )
        return result.scalars().first()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment: {str(e)}"
        )


async def get_user_payments(
    db: AsyncSession,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_status: Optional[PaymentStatusEnum] = None
) -> list[PaymentHistoryResponse]:
    """Retrieve all payments for a user with optional filtering."""

    filters = [Payment.user_id == user_id]

    if start_date:
        filters.append(Payment.created_at >= start_date)
    if end_date:
        filters.append(Payment.created_at <= end_date)
    if payment_status:
        filters.append(Payment.status == payment_status)

    query = (
        select(Payment)
        .options(joinedload(Payment.order))
        .filter(*filters)
        .order_by(Payment.created_at.desc())
    )

    result = await db.execute(query)
    payments = result.scalars().all()

    return [
        PaymentHistoryResponse(
            id=payment.id,
            order_id=payment.order_id,
            amount=payment.amount,
            status=payment.status,
            created_at=payment.created_at,
            stripe_url=payment.order.stripe_url
        ) for payment in payments
    ]
