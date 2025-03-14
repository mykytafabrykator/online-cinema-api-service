from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from database import Order, OrderItem, Cart, User
from schemas import OrderItemResponseSchema, MovieListItemSchema


async def create_order(user_id: int, db: AsyncSession) -> Order:
    """Creates a new order for the current user."""
    result = await db.execute(select(Cart).filter(Cart.user_id == user_id))
    cart = result.scalars().first()

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty."
        )

    try:
        order = Order(
            user_id=user_id, total_amount=sum(
                item.movie.price for item in cart.items
            )
        )
        db.add(order)
        await db.flush()

        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                movie_id=cart_item.movie_id,
                price_at_order=cart_item.movie.price,
            )
            db.add(order_item)

        await db.commit()
        await db.refresh(order)
        return order
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


async def update_order_with_stripe_url(
        order: Order,
        stripe_url: str,
        db: AsyncSession
) -> None:
    """Updates the order with a Stripe URL."""
    try:
        order.stripe_url = stripe_url
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order with Stripe URL: {str(e)}"
        )


async def get_user_orders(
    current_user: User,
    db: AsyncSession,
    user_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    order_status: Optional[str] = None,
) -> List[OrderItemResponseSchema]:
    """Retrieves orders for a specific user or all users for admin."""
    if current_user.group.name != "user":
        filters = []
        if user_id:
            filters.append(Order.user_id == user_id)
        if date_from:
            filters.append(Order.created_at >= date_from)
        if date_to:
            filters.append(Order.created_at <= date_to)
        if order_status:
            filters.append(Order.status == order_status)
        query = select(Order).filter(*filters)
    else:
        if user_id or date_from or date_to or order_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission.",
            )
        query = select(Order).filter(Order.user_id == current_user.id)

    query = query.options(
        joinedload(Order.order_items).joinedload(OrderItem.movie)
    )
    query = query.order_by(Order.created_at.desc())

    result = await db.execute(query)
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No orders found."
        )

    return [
        OrderItemResponseSchema(
            created_at=order.created_at,
            movie=[
                MovieListItemSchema(
                    id=item.movie.id,
                    name=item.movie.name,
                    year=item.movie.year,
                    time=item.movie.time,
                    description=item.movie.description,
                )
                for item in order.order_items
            ],
            price_at_order=order.total_amount,
            status=order.status,
        )
        for order in orders
    ]


async def get_order_by_id(
        db: AsyncSession, order_id: int, current_user_id: Optional[int] = None
) -> Order:
    """Retrieve an order by ID and check permissions."""
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )

    if current_user_id and order.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this order.",
        )

    return order


async def format_order_detail(order: Order) -> OrderItemResponseSchema:
    """Format the order details for the response."""
    return OrderItemResponseSchema(
        created_at=order.created_at,
        movie=[
            MovieListItemSchema(
                id=item.movie.id,
                name=item.movie.name,
                year=item.movie.year,
                time=item.movie.time,
                description=item.movie.description,
            )
            for item in order.order_items
        ],
        price_at_order=order.total_amount,
        status=order.status,
    )
