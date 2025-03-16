from typing import List, Optional, cast

from fastapi import HTTPException
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

from database import (
    Cart,
    CartItem,
    Movie,
    Order,
    OrderItem,
    Payment,
    PaymentItem,
    PaymentStatusEnum,
    User,
)
from schemas import CartItemDetail


async def get_user_cart(user: User, db: AsyncSession) -> Optional[Cart]:
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items).joinedload(CartItem.movie))
        .filter(Cart.user_id == user.id)
    )
    return result.scalars().first()


async def get_cart_item(
        cart: Cart,
        movie_id: int,
        db: AsyncSession
) -> Optional[CartItem]:
    result = await db.execute(
        select(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.movie_id == movie_id)
    )
    return result.scalars().first()


async def create_cart(user: User, db: AsyncSession) -> Cart:
    cart = Cart(user_id=user.id)
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return cart


async def add_cart_item(
        cart: Cart,
        movie: Movie,
        db: AsyncSession
) -> CartItem:
    existing_item = await get_cart_item(cart, movie.id, db)
    if existing_item:
        raise HTTPException(
            status_code=400,
            detail="Movie is already in the cart"
        )

    cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)
    return cart_item


async def delete_cart_item(cart_item: CartItem, db: AsyncSession) -> None:
    await db.delete(cart_item)
    await db.commit()


async def delete_cart_item_by_cart(db: AsyncSession, cart_id: int) -> None:
    await db.execute(
        delete(CartItem).where(CartItem.cart_id == cart_id)
    )
    await db.commit()


async def create_order(db: AsyncSession, order: Order) -> None:
    db.add(order)
    await db.commit()
    await db.refresh(order)


async def create_order_items(
        db: AsyncSession,
        order: Order,
        cart: Cart
) -> List[OrderItem]:
    order_items: List[OrderItem] = []
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            movie_id=item.movie.id,
            price_at_order=item.movie.price
        )
        db.add(order_item)
        order_items.append(order_item)

    return order_items


async def create_payment(
        db: AsyncSession,
        user: User,
        order: Order
) -> Payment:
    payment = Payment(
        user_id=user.id,
        order_id=order.id,
        status=PaymentStatusEnum.PENDING,
        amount=order.total_amount,
        external_payment_id=None
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def create_payment_items(
    db: AsyncSession,
    payment: Payment,
    order_items: List[OrderItem]
) -> None:
    for order_item in order_items:
        payment_item = PaymentItem(
            payment_id=payment.id,
            order_item_id=order_item.id,
            price_at_payment=order_item.price_at_order
        )
        db.add(payment_item)

    await db.commit()


async def process_order_payment_and_clear_cart(
    db: AsyncSession,
    user: User,
    order: Order,
    cart: Cart
) -> Payment:
    order_items = await create_order_items(db, order, cart)
    payment = await create_payment(db, user, order)
    await create_payment_items(db, payment, order_items)

    await delete_cart_item_by_cart(db, cart.id)

    await db.commit()

    return payment


async def is_movie_in_any_cart(db: AsyncSession, movie_id: int) -> bool:
    result = await db.execute(
        select(func.count()).where(CartItem.movie_id == movie_id)
    )
    return result.scalar() > 0


async def delete_movie(db: AsyncSession, movie: Movie) -> None:
    await db.delete(movie)
    await db.commit()


async def get_purchased_movies_from_db(
        user: User,
        db: AsyncSession
) -> List[Movie]:
    result = await db.execute(
        select(Movie)
        .join(OrderItem)
        .join(Order)
        .filter(Order.user_id == user.id, Order.status == "paid")
        .distinct()
    )
    return cast(List[Movie], result.scalars().all())


async def get_cart_items_details(
        cart: Optional[Cart],
        db: AsyncSession
) -> List[CartItemDetail]:
    if not cart:
        return []

    result = await db.execute(
        select(CartItem)
        .options(joinedload(CartItem.movie).joinedload(Movie.genres))
        .filter(CartItem.cart_id == cart.id)
    )

    cart_items = result.unique().scalars().all()

    return [
        CartItemDetail(
            movie_id=item.movie.id,
            title=item.movie.name,
            price=item.movie.price,
            genre=item.movie.genres[0].name if item.movie.genres else "Unknown",  # noqa: E501
            release_year=item.movie.year
        )
        for item in cart_items
    ]
