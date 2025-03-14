from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from database import (
    Certification,
    Director,
    Genre,
    Movie,
    Star,
    FavoriteMovie,
    MovieLike
)
from schemas import MovieCreateSchema, MovieSortEnum


async def get_movies_paginated(
    db: AsyncSession, page: int, per_page: int
) -> tuple[int, list[Movie]]:
    offset = (page - 1) * per_page

    total_items = await db.scalar(select(func.count()).select_from(Movie))

    query = select(Movie).order_by(Movie.id).offset(offset).limit(per_page)
    result = await db.execute(query)
    movies = result.scalars().all()

    return total_items, movies


async def filter_movies(
    db: AsyncSession,
        filters: dict[str, str],
        sort_by: Optional[MovieSortEnum] = None
) -> list[Movie]:
    query = select(Movie)

    if "name" in filters:
        query = query.filter(Movie.name.ilike(f"%{filters['name']}%"))
    if "year" in filters:
        query = query.filter(Movie.year == filters["year"])
    if "min_imdb" in filters:
        query = query.filter(Movie.imdb >= filters["min_imdb"])
    if "max_imdb" in filters:
        query = query.filter(Movie.imdb <= filters["max_imdb"])
    if "min_votes" in filters:
        query = query.filter(Movie.votes >= filters["min_votes"])
    if "max_votes" in filters:
        query = query.filter(Movie.votes <= filters["max_votes"])
    if "min_price" in filters:
        query = query.filter(Movie.price >= filters["min_price"])
    if "max_price" in filters:
        query = query.filter(Movie.price <= filters["max_price"])

    if sort_by:
        query = query.order_by(getattr(Movie, sort_by.value))
    else:
        query = query.order_by(Movie.id)

    result = await db.execute(query)
    return result.scalars().all()


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> Optional[Movie]:
    result = await db.execute(select(Movie).filter(Movie.id == movie_id))
    return result.scalars().first()


async def get_detail_movies_by_id(
        db: AsyncSession,
        movie_id: int
) -> Optional[Movie]:
    result = await db.execute(
        select(Movie)
        .options(
            joinedload(Movie.certification),
            joinedload(Movie.genres),
            joinedload(Movie.stars),
            joinedload(Movie.directors),
        )
        .filter(Movie.id == movie_id)
    )
    return result.scalars().first()


async def get_movie_by_name(
        db: AsyncSession,
        movie_data: MovieCreateSchema
) -> Optional[Movie]:
    result = await db.execute(
        select(Movie).filter(Movie.name == movie_data.name)
    )
    return result.scalars().first()


async def get_or_create_certification(
        db: AsyncSession,
        name: str
) -> Certification:
    result = await db.execute(select(Certification).filter_by(name=name))
    certification = result.scalars().first()
    if not certification:
        certification = Certification(name=name)
        db.add(certification)
        await db.commit()
        await db.refresh(certification)

    return certification


async def get_or_create_entities(
        db: AsyncSession,
        model,
        names: list[str]
) -> list[Any]:
    objects = []
    for name in names:
        result = await db.execute(select(model).filter_by(name=name))
        entity = result.scalars().first()
        if not entity:
            entity = model(name=name)
            db.add(entity)
            await db.flush()
        objects.append(entity)
    return objects


async def create_movie_post(
        db: AsyncSession,
        movie_data: MovieCreateSchema
) -> Movie:
    certification = await get_or_create_certification(
        db,
        movie_data.certification
    )
    genres = await get_or_create_entities(db, Genre, movie_data.genres)
    stars = await get_or_create_entities(db, Star, movie_data.stars)
    directors = await get_or_create_entities(
        db,
        Director,
        movie_data.directors
    )

    movie = Movie(
        name=movie_data.name,
        year=movie_data.year,
        time=movie_data.time,
        imdb=movie_data.imdb,
        votes=movie_data.votes,
        price=movie_data.price,
        description=movie_data.description,
        certification_id=certification.id,
        genres=genres,
        stars=stars,
        directors=directors,
    )

    db.add(movie)
    await db.commit()
    await db.refresh(movie)

    return movie


async def toggle_movie_like(
        db: AsyncSession,
        movie: Movie,
        user_id: int,
        is_liked: bool
) -> MovieLike:
    result = await db.execute(
        select(MovieLike).filter_by(movie_id=movie.id, user_id=user_id)
    )
    movie_like = result.scalars().first()

    if movie_like:
        await db.delete(movie_like)
    else:
        movie_like = MovieLike(
            user_id=user_id,
            movie_id=movie.id,
            is_liked=is_liked
        )
        db.add(movie_like)

    await db.commit()
    return movie_like


async def toggle_movie_favorite(
        db: AsyncSession,
        movie: Movie,
        user_id: int,
        is_favorited: bool
) -> FavoriteMovie:
    result = await db.execute(
        select(FavoriteMovie).filter_by(movie_id=movie.id, user_id=user_id)
    )
    movie_fav = result.scalars().first()

    if movie_fav:
        await db.delete(movie_fav)
    else:
        movie_fav = FavoriteMovie(
            user_id=user_id,
            movie_id=movie.id,
            is_favorited=is_favorited
        )
        db.add(movie_fav)

    await db.commit()
    return movie_fav


async def delete_instance(db: AsyncSession, instance: Any) -> None:
    await db.delete(instance)
    await db.commit()


async def commit_instance(db: AsyncSession, instance: Any) -> None:
    await db.commit()
    await db.refresh(instance)
