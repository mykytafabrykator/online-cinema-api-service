from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import (
    Order,
    get_db
)
from database.crud.accounts import get_user_by_id
from database.crud.movies import get_movie_by_id
from database.crud.shopping_cart import (
    add_cart_item,
    create_cart,
    create_order,
    delete_cart_item,
    delete_cart_item_by_cart,
    get_cart_item,
    get_cart_items_details,
    get_purchased_movies_from_db,
    get_user_cart,
    process_order_payment_and_clear_cart,
)
from schemas.accounts import MessageResponseSchema
from schemas.shopping_cart import (
    CartCreate,
    CartItemResponse,
    CartResponse,
    PurchasedMoviesResponse,
)
from security import JWTAuthManagerInterface
from security.http import get_token
from database.validators.shopping_cart import (
    validate_movie_availability,
    validate_not_in_cart,
    validate_not_purchased,
)

router = APIRouter()


@router.get(
    "/",
    response_model=CartResponse,
    summary="Get user's shopping cart",
    responses={
        404: {"description": "User not found."},
        401: {"description": "Unauthorized request."}
    }
)
async def get_cart(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> CartResponse:
    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    cart = await get_user_cart(user, db)
    if not cart:
        return CartResponse(user_id=user.id, movies=[])

    cart_items = await get_cart_items_details(cart, db)

    return CartResponse(user_id=user.id, movies=cart_items)


@router.post(
    "/add/",
    response_model=CartResponse,
    summary="Add a movie to the shopping cart",
    responses={
        404: {"description": "User or movie not found."},
        400: {"description": "Movie already in cart."},
        401: {"description": "Unauthorized request."}
    }
)
async def add_to_cart(
        cart_data: CartCreate,
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> CartResponse:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    movie = await get_movie_by_id(db, cart_data.movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    await validate_movie_availability(movie)
    await validate_not_in_cart(user, movie, db)
    await validate_not_purchased(user, movie, db)

    cart = await get_user_cart(user, db) or await create_cart(user, db)
    await add_cart_item(cart, movie, db)
    await db.refresh(cart)

    cart_items = await get_cart_items_details(cart, db)

    return CartResponse(user_id=user.id, movies=cart_items)


@router.delete(
    "/remove/{movie_id}",
    response_model=CartItemResponse,
    summary="Remove a movie from the shopping cart",
    responses={
        404: {"description": "Movie or cart not found."},
        401: {"description": "Unauthorized request."}
    }
)
async def remove_from_cart(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> CartItemResponse:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    cart = await get_user_cart(user, db)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_item = await get_cart_item(cart, movie_id, db)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Movie not in cart")

    await delete_cart_item(cart_item, db)
    return CartItemResponse(message="Movie removed from cart")


@router.delete(
    "/clear/",
    response_model=CartItemResponse,
    summary="Clear the shopping cart",
    responses={
        404: {"description": "Cart already empty."},
        401: {"description": "Unauthorized request."}
    }
)
async def clear_cart(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> CartItemResponse:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    cart = await get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=404, detail="Cart is already empty")

    await delete_cart_item_by_cart(db, cart.id)

    return CartItemResponse(message="Cart cleared successfully")


@router.post(
    "/checkout/",
    response_model=MessageResponseSchema,
    summary="Checkout and complete purchase",
    responses={
        404: {"description": "User not found."},
        403: {"description": "User not activated."},
        400: {"description": "Cart is empty."},
        401: {"description": "Unauthorized request."}
    }
)
async def checkout(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> MessageResponseSchema:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Please activate your account before making a purchase."
        )

    cart = await get_user_cart(user, db)
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Your cart is empty")

    order = Order(
        user_id=user.id,
        total_amount=sum(item.movie.price for item in cart.items)
    )

    await create_order(db, order)

    await process_order_payment_and_clear_cart(db, user, order, cart)

    return MessageResponseSchema(
        message="Order placed successfully. Payment has been created."
    )


@router.get(
    "/purchased/",
    response_model=PurchasedMoviesResponse,
    summary="Retrieve purchased movies",
    responses={
        404: {"description": "User not found."},
        401: {"description": "Unauthorized request."}
    }
)
async def get_purchased_movies(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(get_token),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager)
) -> PurchasedMoviesResponse:

    token_data = jwt_manager.decode_access_token(token)
    user_id = token_data["user_id"]

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given ID was not found."
        )

    purchased_movies = await get_purchased_movies_from_db(user, db)
    return PurchasedMoviesResponse(
        purchased_movies=[movie.name for movie in purchased_movies]
    )
