from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Genre
from database.crud.movies import get_all_genres
from schemas import GenreResponseSchema

router = APIRouter()


@router.get(
    "/",
    summary="Get list of all genres",
    response_model=List[GenreResponseSchema],
    description=(
        "Fetches a list of all movie genres available in the database. "
        "Each genre includes its unique ID and name. This endpoint is useful "
        "for filtering movies by genre or displaying a category list to users."
    ),
    response_description="A list of genres, each containing an ID and name.",
)
async def get_genres(
        db: AsyncSession = Depends(get_db)
) -> list[Genre]:
    """
    Retrieves all genres stored in the database.

    Returns:
        List[GenreResponseSchema]: A list of genre objects.

    Raises:
        HTTPException 500: If there is an issue retrieving genres.
    """
    return await get_all_genres(db)
