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



