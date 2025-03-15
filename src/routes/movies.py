from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.crud.movies import filter_movies, get_movie_by_id
from schemas import (
    MovieListResponseSchema,
    MovieSortEnum,
    MovieListItemSchema,
    MovieDetailSchema
)

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
