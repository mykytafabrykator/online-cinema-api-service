from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Star
from database.crud.movies import (
    get_all_instances,
    get_or_create_model,
    delete_instance,
    get_instance_by_id,
    commit_instance,
)
from schemas import StarsSchema, StarsResponseSchema, DetailMessageSchema

router = APIRouter()


@router.get(
    "/",
    summary="Get list of all stars",
    response_model=List[StarsResponseSchema],
    response_description="A list of stars, each containing an ID and name.",
)
async def get_stars(
        db: AsyncSession = Depends(get_db)
) -> list[Star]:
    """
    Retrieves all stars stored in the database.

    Returns:
        List[StarsResponseSchema]: A list of star objects.

    Raises:
        HTTPException 500: If there is an issue retrieving stars.
    """
    return await get_all_instances(db, Star)


@router.post(
    "/",
    summary="Create a new star",
    status_code=201,
    description=(
        "Adds a new star to the database. If the star already exists, "
        "it returns a conflict error (409)."
    ),
    responses={
        201: {"description": "Star created successfully."},
        409: {
            "description": "Star already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with this name already exists."
                    }
                }
            },
        },
    },
)
async def create_star(
        star_data: StarsSchema,
        db: AsyncSession = Depends(get_db)
) -> StarsResponseSchema:
    """
    Creates a new star in the database.

    Args:
        star_data (StarsSchema): The star data containing the name.
        db (AsyncSession): The database session.

    Returns:
        StarsResponseSchema: The created star object.

    Raises:
        HTTPException 409: If the star already exists.
    """
    star, created = await get_or_create_model(db, Star, star_data.name)

    if not created:
        raise HTTPException(
            status_code=409,
            detail="Star with this name already exists."
        )

    return StarsResponseSchema.model_validate(star)


@router.delete(
    "/{star_id}/",
    summary="Delete a star by ID",
    status_code=204,
    responses={
        204: {
            "description": "Star deleted successfully."
        },
        404: {
            "description": "Star not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with the given ID was not found."
                    }
                }
            },
        },
    },
)
async def delete_star(
        star_id: int,
        db: AsyncSession = Depends(get_db),
) -> None:
    """
       Delete a specific star from the database by its unique ID.

       This function removes a star from the database.
       If the star does not exist,
       a 404 error is raised.

       Returns:
       - No content (status code 204) on successful deletion.

       Raises:
       - `HTTPException 404`: If the star with the given ID does not exist.
       """
    star = await get_instance_by_id(db, Star, star_id)

    if not star:
        raise HTTPException(status_code=404, detail="Star not found")

    await delete_instance(db, star)
    return


@router.patch(
    "/{star_id}/",
    response_model=DetailMessageSchema,
    summary="Update star by ID",
    status_code=200,
    responses={
        200: {
            "description": "Star updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star updated successfully."}
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
            "description": "Star not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Star not found."}
                }
            },
        },
    },
)
async def update_star(
        star_id: int,
        star_data: StarsSchema,
        db: AsyncSession = Depends(get_db),
) -> DetailMessageSchema:
    """
    Updates an existing star by its ID with provided data.
    """
    star = await get_instance_by_id(db, Star, star_id)

    if not star:
        raise HTTPException(status_code=404, detail="Star not found")

    for field, value in star_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(star, field, value)

    try:
        await commit_instance(db, star)
    except HTTPException:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return DetailMessageSchema(detail="Star updated successfully.")
