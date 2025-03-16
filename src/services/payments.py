import stripe

from config import get_settings
from database import Order


settings = get_settings()

SUCCESS_URL = "http://localhost:8000/api/v1/payments/"
CANCEL_URL = "http://localhost:8000/api/v1/payments/"

stripe.api_key = settings.STRIPE_SECRET_KEY


async def create_stripe_session(order: Order) -> str:
    """
    Create a new Stripe Checkout Session for an Order.
    """
    total_price = order.total_amount
    unit_amount = int(total_price * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Payment for order №{order.id}",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
    )

    return session.url
