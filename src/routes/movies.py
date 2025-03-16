from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, User
from database.crud.movies import (
    filter_movies,
    get_movie_by_id,
    get_movie_by_name,
    create_movie_post,
    delete_instance,
    commit_instance,
    toggle_movie_like,
    toggle_movie_favorite,
)
from schemas import (
    MovieListResponseSchema,
    MovieSortEnum,
    MovieListItemSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    DetailMessageSchema,
    MovieUpdateSchema,
    MovieLikeResponseSchema,
    MovieFavoriteResponseSchema,
)
from utils import get_current_user

router = APIRouter()


@router.get(
    "/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies with optional "
            "filtering and sorting"
)
async def get_movies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(
        None,
        description="Search by title or description"
    ),
    year: Optional[int] = Query(
        None,
        description="Filter by release year"
    ),
    min_imdb: Optional[float] = Query(
        None,
        description="Filter by minimum IMDb rating"
    ),
    max_imdb: Optional[float] = Query(
        None,
        description="Filter by maximum IMDb rating"
    ),
    min_price: Optional[float] = Query(
        None,
        description="Filter by minimum price"
    ),
    max_price: Optional[float] = Query(
        None,
        description="Filter by maximum price"
    ),
    sort_by: Optional[MovieSortEnum] = Query(
        None,
        description="Sort movies by criteria"
    ),
):
    """
    Retrieves a paginated list of movies with optional filtering,
    searching, and sorting.

    - `page`: Page number (default: 1)
    - `per_page`: Number of movies per page (default: 10, max: 100)
    - `search`: Search movies by name or description (optional)
    - `year`: Filter by release year (optional)
    - `min_imdb`, `max_imdb`: Filter by IMDb rating (optional)
    - `min_price`, `max_price`: Filter by price range (optional)
    - `sort_by`: Sorting option (optional)
    """
    filters = {
        "name": search,
        "year": year,
        "min_imdb": min_imdb,
        "max_imdb": max_imdb,
        "min_price": min_price,
        "max_price": max_price,
    }

    filtered_movies = await filter_movies(db, filters, sort_by)

    total_items = len(filtered_movies)
    total_pages = (total_items + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page

    paginated_movies = filtered_movies[start:end]

    if not paginated_movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    return MovieListResponseSchema(
        movies=[
            MovieListItemSchema.model_validate(movie)
            for movie in paginated_movies
        ],
        prev_page=(
            f"/movies/?page={page - 1}&per_page={per_page}"
            if page > 1 else None
        ),
        next_page=(
            f"/movies/?page={page + 1}&per_page={per_page}"
            if page < total_pages else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Retrieve movie details by ID",
)
async def get_movie_detail(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
    Retrieves detailed information about a movie.

    Returns:
        MovieDetailSchema: The detailed information of the requested movie.

    Raises:
        HTTPException: If the movie is not found (404).
    """
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return MovieDetailSchema.model_validate(movie)


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=201,
    summary="Create a new movie",
)
async def create_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
       Creates a new movie entry in the database.

       Args:
           movie_data (MovieCreateSchema): The movie details to be created.
           db (AsyncSession): Database session dependency.

       Returns:
           MovieDetailSchema: The created movie details
           including genres, stars, and directors.

       Raises:
           HTTPException 409: If a movie with the same name,
           year, and time already exists.
           HTTPException 400: If the provided data is invalid.
       """
    existing_movie = await get_movie_by_name(db, movie_data)

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail="Movie already exists.",
        )

    try:
        movie = await create_movie_post(db, movie_data)
        return MovieDetailSchema.model_validate(movie)
    except HTTPException:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.delete(
    "/{movie_id}/",
    summary="Delete a movie by ID",
    status_code=204,
    responses={
        204: {
            "description": "Movie deleted successfully."
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with the given ID was not found."
                    }
                }
            },
        },
    },
)
async def delete_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
) -> None:
    """
       Delete a specific movie from the database by its unique ID.

       This function removes a movie from the database.
       If the movie does not exist,
       a 404 error is raised.

       Returns:
       - No content (status code 204) on successful deletion.

       Raises:
       - `HTTPException 404`: If the movie with the given ID does not exist.
       """
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    await delete_instance(db, movie)
    return


@router.patch(
    "/{movie_id}/",
    response_model=DetailMessageSchema,
    summary="Update movie by ID",
    status_code=200,
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie updated successfully."}
                }
            },
        },
        400: {
            "description": "Invalid input data.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie not found."}
                }
            },
        },
    },
)
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db),
) -> DetailMessageSchema:
    """
    Updates an existing movie by its ID with partial or full data.

    This endpoint allows users to update movie details such as name,
    year, duration, IMDb rating, votes, price, description, and more.

    - Fields that are not provided in the request body remain unchanged.
    - Updating related entities like genres, stars, and directors
    is **not allowed**.

    Args:
        movie_id (int): The ID of the movie to be updated.
        movie_data (MovieUpdateSchema):
        The updated movie data (only the fields that need to be modified).
        db (AsyncSession, optional): The database session dependency.

    Returns:
    - DetailMessageSchema: A success message if
    the movie is updated successfully.

    Raises:
    - HTTPException 404: If the movie with the given ID does not exist.
    - HTTPException 400: If the provided input data is invalid.
    """
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(movie, field, value)

    try:
        await commit_instance(db, movie)
    except HTTPException:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return DetailMessageSchema(detail="Movie updated successfully.")


@router.post(
    "/{movie_id}/like/",
    response_model=MovieLikeResponseSchema,
    summary="Like or dislike a movie",
    responses={
        200: {"description": "Movie like status updated."},
        404: {
            "description": "Movie or user not found.",
            "content": {
                "application/json":
                    {
                        "example": {
                            "detail": "Movie with the given ID was not found."
                        }
                    }
            }
        },
        401: {
            "description": "Unauthorized access.",
            "content":
                {
                    "application/json":
                        {
                            "example":
                                {
                                    "detail": "Invalid or expired token."
                                }
                        }
                }
        },
    }
)
async def like_or_dislike(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
) -> MovieLikeResponseSchema:
    """
    Toggle like or dislike for a specific movie.

    **Parameters:**
    - `movie_id` (int): The unique identifier of the movie.

    **Returns:**
    - `MovieLikeResponseSchema`: The updated like status and
    associated movie/user info.

    **Raises:**
    - `HTTPException 404`: If the movie or user is not found.
    - `HTTPException 401`: If the token is invalid or expired.
    """
    movie = await get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    movie_like = await toggle_movie_like(db, movie, user.id)

    return MovieLikeResponseSchema(
        is_liked=movie_like.is_liked,
        created_at=movie_like.created_at,
        user=user,
        movie=movie,
    )


@router.post(
    "/{movie_id}/favorite/",
    response_model=MovieFavoriteResponseSchema,
    summary="Add or remove a movie from favorites",
    responses={
        200: {"description": "Movie favorite status updated."},
        404: {
            "description": "Movie or user not found.",
            "content": {
                "application/json":
                    {
                        "example": {
                            "detail": "Movie with the given ID was not found."
                        }
                    }
            }
        },
        401: {
            "description": "Unauthorized access.",
            "content":
                {
                    "application/json":
                        {
                            "example":
                                {
                                    "detail": "Invalid or expired token."
                                }
                        }
                }
        },
    }
)
async def favorite_or_unfavorite(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
) -> MovieFavoriteResponseSchema:
    """
    Toggle favorite status for a specific movie.

    **Parameters:**
    - `movie_id` (int): The unique identifier of the movie.

    **Returns:**
    - `MovieFavoriteResponseSchema`: The updated favorite status and
    associated movie/user info.

    **Raises:**
    - `HTTPException 404`: If the movie or user is not found.
    - `HTTPException 401`: If the token is invalid or expired.
    """
    movie = await get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    movie_favorite = await toggle_movie_favorite(db, movie, user.id)

    return MovieFavoriteResponseSchema(
        is_favorited=movie_favorite.is_favorited,
        created_at=movie_favorite.created_at,
        user=movie_favorite.user,
        movie=movie_favorite.movie,
    )
