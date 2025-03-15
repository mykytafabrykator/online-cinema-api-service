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

    if filters.get("name"):
        query = query.filter(Movie.name.ilike(f"%{filters['name']}%"))
    if filters.get("year") is not None:
        query = query.filter(Movie.year == filters["year"])
    if filters.get("min_imdb") is not None:
        query = query.filter(Movie.imdb >= float(filters["min_imdb"]))
    if filters.get("max_imdb") is not None:
        query = query.filter(Movie.imdb <= float(filters["max_imdb"]))
    if filters.get("min_price") is not None:
        query = query.filter(Movie.price >= float(filters["min_price"]))
    if filters.get("max_price") is not None:
        query = query.filter(Movie.price <= float(filters["max_price"]))

    if sort_by:
        if sort_by == MovieSortEnum.PRICE_ASC:
            query = query.order_by(Movie.price)
        elif sort_by == MovieSortEnum.PRICE_DESC:
            query = query.order_by(Movie.price.desc())
        elif sort_by == MovieSortEnum.RELEASE_YEAR_ASC:
            query = query.order_by(Movie.year)
        elif sort_by == MovieSortEnum.RELEASE_YEAR_DESC:
            query = query.order_by(Movie.year.desc())
        elif sort_by == MovieSortEnum.VOTES_ASC:
            query = query.order_by(Movie.votes)
        elif sort_by == MovieSortEnum.VOTES_DESC:
            query = query.order_by(Movie.votes.desc())
        elif sort_by == MovieSortEnum.IMDb_ASC:
            query = query.order_by(Movie.imdb)
        elif sort_by == MovieSortEnum.IMDb_DESC:
            query = query.order_by(Movie.imdb.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_movie_by_id(db: AsyncSession, movie_id: int) -> Optional[Movie]:
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

    result = await db.execute(
        select(Movie)
        .options(
            joinedload(Movie.certification),
            joinedload(Movie.genres),
            joinedload(Movie.stars),
            joinedload(Movie.directors),
        )
        .filter(Movie.id == movie.id)
    )
    movie_with_relations = result.scalars().first()

    return movie_with_relations


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


async def get_all_instances(db: AsyncSession, instance: Any) -> list[Any]:
    result = await db.execute(select(instance))
    return result.scalars().all()


async def get_or_create_model(
        db: AsyncSession,
        instance: Any,
        name: str
) -> tuple[Any, bool]:
    result = await db.execute(select(instance).filter_by(name=name))
    model = result.scalars().first()

    if model:
        return model, False

    model = instance(name=name)
    db.add(model)
    await db.commit()
    await db.refresh(model)

    return model, True


async def get_instance_by_id(db: AsyncSession, instance: Any, instance_id: int) -> Optional[Any]:
    result = await db.execute(select(instance).filter_by(id=instance_id))
    return result.scalars().first()
