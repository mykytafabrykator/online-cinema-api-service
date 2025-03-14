from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import Cart, CartItem, Movie, User


async def validate_movie_availability(movie: Movie | None) -> None:
    if not movie:
        raise HTTPException(
            status_code=400,
            detail="Movie is not available for purchase."
        )


async def validate_not_purchased(
        user: User,
        movie: Movie,
        db: AsyncSession
) -> None:
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .filter(
            Cart.user_id == user.id,
            CartItem.movie_id == movie.id
        )
    )
    purchased_movie = result.scalars().first()

    if purchased_movie:
        raise HTTPException(
            status_code=400,
            detail="You have already purchased this movie."
        )


async def validate_not_in_cart(
        user: User,
        movie: Movie,
        db: AsyncSession
) -> None:
    result = await db.execute(select(Cart).filter(Cart.user_id == user.id))
    cart = result.scalars().first()

    if cart:
        result = await db.execute(
            select(CartItem)
            .filter(
                CartItem.cart_id == cart.id,
                CartItem.movie_id == movie.id
            )
        )
        existing_item = result.scalars().first()

        if existing_item:
            raise HTTPException(
                status_code=400,
                detail="Movie already in cart."
            )
