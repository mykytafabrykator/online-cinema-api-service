from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Genre
from database.crud.movies import get_all_genres, get_or_create_genre
from schemas import GenreResponseSchema, GenresSchema

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


@router.post(
    "/",
    summary="Create a new genre",
    status_code=201,
    description=(
        "Adds a new genre to the database. If the genre already exists, "
        "it returns a conflict error (409)."
    ),
    responses={
        201: {"description": "Genre created successfully."},
        409: {
            "description": "Genre already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with this name already exists."
                    }
                }
            },
        },
    },
)
async def create_genre(
        genre_data: GenresSchema,
        db: AsyncSession = Depends(get_db)
) -> GenreResponseSchema:
    """
    Creates a new genre in the database.

    Args:
        genre_data (GenresSchema): The genre data containing the name.
        db (AsyncSession): The database session.

    Returns:
        GenreResponseSchema: The created genre object.

    Raises:
        HTTPException 409: If the genre already exists.
    """
    genre, created = await get_or_create_genre(db, genre_data.name)

    if not created:
        raise HTTPException(
            status_code=409,
            detail="Genre with this name already exists."
        )

    return GenreResponseSchema.model_validate(genre)
