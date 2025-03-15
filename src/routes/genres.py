from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Genre
from database.crud.movies import (
    get_all_instances,
    get_or_create_model,
    delete_instance,
    get_instance_by_id,
    commit_instance,
)
from schemas import GenreResponseSchema, GenresSchema, DetailMessageSchema

router = APIRouter()


@router.get(
    "/",
    summary="Get list of all genres",
    response_model=List[GenreResponseSchema],
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
    return await get_all_instances(db, Genre)


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
    genre, created = await get_or_create_model(db, Genre, genre_data.name)

    if not created:
        raise HTTPException(
            status_code=409,
            detail="Genre with this name already exists."
        )

    return GenreResponseSchema.model_validate(genre)


@router.delete(
    "/{genre_id}/",
    summary="Delete a genre by ID",
    status_code=204,
    responses={
        204: {
            "description": "Genre deleted successfully."
        },
        404: {
            "description": "Genre not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with the given ID was not found."
                    }
                }
            },
        },
    },
)
async def delete_genre(
        genre_id: int,
        db: AsyncSession = Depends(get_db),
) -> None:
    """
       Delete a specific genre from the database by its unique ID.

       This function removes a genre from the database.
       If the genre does not exist,
       a 404 error is raised.

       Returns:
       - No content (status code 204) on successful deletion.

       Raises:
       - `HTTPException 404`: If the genre with the given ID does not exist.
       """
    genre = await get_instance_by_id(db, Genre, genre_id)

    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    await delete_instance(db, genre)
    return


@router.patch(
    "/{genre_id}/",
    response_model=DetailMessageSchema,
    summary="Update genre by ID",
    status_code=200,
    responses={
        200: {
            "description": "Genre updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre updated successfully."}
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
            "description": "Genre not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Genre not found."}
                }
            },
        },
    },
)
async def update_genre(
        genre_id: int,
        genre_data: GenresSchema,
        db: AsyncSession = Depends(get_db),
) -> DetailMessageSchema:
    """
    Updates an existing genre by its ID with provided data.
    """
    genre = await get_instance_by_id(db, Genre, genre_id)

    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    for field, value in genre_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(genre, field, value)

    try:
        await commit_instance(db, genre)
    except HTTPException:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return DetailMessageSchema(detail="Genre updated successfully.")
