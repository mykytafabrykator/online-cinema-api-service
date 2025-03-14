from typing import Any, Optional

from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup
)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).filter_by(email=email)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_group_by_name(
        db: AsyncSession,
        name: str
) -> Optional[UserGroup]:
    stmt = select(UserGroup).filter_by(name=name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).filter_by(id=user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_user_group_by_name(db: AsyncSession, name: str) -> UserGroup:
    user_group = UserGroup(name=name)
    db.add(user_group)
    await db.commit()
    await db.refresh(user_group)
    return user_group


async def create_user_by_email_password_group_id(
        db: AsyncSession,
        email: str,
        password: str,
        group_id: int
) -> tuple[User, ActivationToken]:
    new_user = User.create(
        email=str(email),
        raw_password=password,
        group_id=group_id,
    )
    db.add(new_user)
    await db.flush()

    activation_token = ActivationToken(user_id=new_user.id)
    db.add(activation_token)

    await db.commit()
    await db.refresh(new_user)
    return new_user, activation_token


async def get_activation_token_by_email_token(
        db: AsyncSession,
        email: str,
        token: str
) -> Optional[ActivationToken]:
    stmt = (
        select(ActivationToken)
        .options(joinedload(ActivationToken.user))
        .join(User)
        .filter(
            User.email == email,
            ActivationToken.token == token,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def delete_token(db: AsyncSession, token: Any) -> None:
    await db.delete(token)
    await db.commit()


async def delete_password_reset_token_by_user_id(
        db: AsyncSession,
        user_id: int
) -> None:
    stmt = delete(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id
    )
    await db.execute(stmt)
    await db.commit()


async def create_password_reset_token_by_user_id(
        db: AsyncSession,
        user_id: int
) -> PasswordResetToken:
    reset_token = PasswordResetToken(user_id=user_id)
    db.add(reset_token)
    await db.commit()
    return reset_token


async def get_password_reset_token_by_user_id(
        db: AsyncSession,
        user_id: int
) -> Optional[PasswordResetToken]:
    stmt = select(PasswordResetToken).filter_by(user_id=user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def db_rollback(db: AsyncSession) -> None:
    await db.rollback()


async def create_refresh_token_by_user_id_days_token(
        db: AsyncSession,
        user_id: int,
        days_valid: int,
        token: str
) -> None:
    refresh_token = RefreshToken.create(
        user_id=user_id,
        days_valid=days_valid,
        token=token,
    )
    db.add(refresh_token)
    await db.flush()
    await db.commit()


async def get_refresh_token_by_refresh_token(
        db: AsyncSession,
        refresh_token: str
) -> Optional[RefreshToken]:
    stmt = select(RefreshToken).filter_by(token=refresh_token)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_all_activation_tokens(db: AsyncSession) -> list[ActivationToken]:
    stmt = select(ActivationToken)
    result = await db.execute(stmt)
    return result.scalars().all()


async def remove_activation_token(db: AsyncSession, token: Any) -> None:
    await db.delete(token)
    await db.commit()


async def create_activation_token_by_user_id(
    db: AsyncSession,
    user_id: int
) -> ActivationToken:
    new_token = ActivationToken(user_id=user_id)
    db.add(new_token)
    await db.commit()
    return new_token


async def get_latest_activation_token_by_email(
        db: AsyncSession,
        email: str
) -> Optional[ActivationToken]:
    stmt = (
        select(ActivationToken)
        .options(joinedload(ActivationToken.user))
        .join(User)
        .filter(User.email == email)
        .order_by(desc(ActivationToken.expires_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()
