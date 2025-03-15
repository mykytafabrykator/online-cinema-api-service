from typing import Optional

import stripe
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import get_settings
from database import Order, Payment, PaymentStatusEnum
from database.crud.payments import create_payment, create_payment_items
from exceptions import handle_stripe_error
from schemas import PaymentCreateSchema

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_checkout_session(
    request: Request,
    order: Order,
    user_id: int,
    db: AsyncSession,
) -> Optional[str]:
    """
    Creates a Stripe checkout session for a given order.

    Args:
        request (Request): The FastAPI request object.
        order (Order): The order object containing order details.
        user_id (int): The ID of the user making the payment.
        db (AsyncSession): The SQLAlchemy database session.
    Returns:
        str | None: The URL of the created Stripe checkout session,
                    or None if the session couldn't be created.
    """
    try:
        result = await db.execute(
            select(Payment).filter_by(
                order_id=order.id,
                status=PaymentStatusEnum.PENDING
            )
        )
        existing_payment = result.scalars().first()

        if existing_payment and existing_payment.external_payment_id:
            try:
                session = await stripe.checkout.Session.retrieve(
                    existing_payment.external_payment_id
                )
                return session.url
            except stripe.error.StripeError as e:
                handle_stripe_error(e)

        if not order.total_amount or not order.order_items:
            raise ValueError(
                "Order must have a valid total amount and at least one item."
            )

        product_data = " | ".join(
            [f"{item.movie.name} x {item.price_at_order}"
             for item in order.order_items]
        )

        success_url = f"{request.url_for(
            'payment_success'
        )}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{request.url_for(
            'payment_cancel'
        )}?session_id={{CHECKOUT_SESSION_ID}}"

        try:
            session = await stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": product_data},
                            "unit_amount": int(order.total_amount * 100),
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except stripe.error.StripeError as e:
            handle_stripe_error(e)

        new_payment = PaymentCreateSchema(
            user_id=user_id,
            order_id=order.id,
            amount=order.total_amount,
            external_payment_id=session.id,
        )

        created_payment = await create_payment(new_payment, db)
        if created_payment:
            await create_payment_items(created_payment, order, db)
            return session.url

        return None

    except stripe.error.StripeError as e:
        handle_stripe_error(e)
