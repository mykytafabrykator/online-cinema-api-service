from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import (
    get_db,
    User,
    UserGroup,
    UserGroupEnum,
    ActivationToken,
    PasswordResetToken,
)
from src.schemas import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    MessageResponseSchema,
    UserActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
)


router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email "
                                  "test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
                           "An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        },
    }
)
async def register_user(
        user_data: UserRegistrationRequestSchema,
        db: AsyncSession = Depends(get_db),
) -> UserRegistrationResponseSchema:
    """
    Endpoint for user registration.

    Registers a new user, hashes their password,
    and assigns them to the default user group.

    If a user with the same email already exists,
    an HTTP 409 error is raised.

    In case of any unexpected issues during the creation process,
    an HTTP 500 error is returned.

    Args:
        user_data (UserRegistrationRequestSchema):
        The registration details including email and password.
        db (AsyncSession): The asynchronous database session.

    Returns:
        UserRegistrationResponseSchema: The newly created user's details.

    Raises:
        HTTPException:
            - 409 Conflict if a user with the same email exists.
            - 500 Internal Server Error
            if an error occurs during user creation.
    """
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result = await db.execute(stmt)
    user_group = result.scalars().first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

    try:
        new_user = User.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationToken(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e
    else:
        return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate User Account",
    description="Activate a user's account using "
                "their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token "
                           "is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or "
                                          "expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    },
)
async def activate_account(
        activation_data: UserActivationRequestSchema,
        db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """
    Endpoint to activate a user's account.

    This endpoint verifies the activation token for a user
    by checking that the token record exists
    and that it has not expired. If the token is valid
    and the user's account is not already active,
    the user's account is activated and the activation
    token is deleted. If the token is invalid, expired,
    or if the account is already active, an HTTP 400 error is raised.

    Args:
        activation_data (UserActivationRequestSchema):
        Contains the user's email and activation token.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: A response message
        confirming successful activation.

    Raises:
        HTTPException:
            - 400 Bad Request if the activation token is invalid or expired.
            - 400 Bad Request if the user account is already active.
    """
    stmt = (
        select(ActivationToken)
        .options(joinedload(ActivationToken.user))
        .join(User)
        .where(
            User.email == activation_data.email,
            ActivationToken.token == activation_data.token
        )
    )
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    expire_date = cast(
        datetime,
        token_record.expires_at
    ).replace(tzinfo=timezone.utc)

    if not token_record or expire_date < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    return MessageResponseSchema(
        message="User account activated successfully."
    )


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
            "Allows a user to request a password reset token. "
            "If the user exists and is active, "
            "a new token will be generated and "
            "any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
)
async def request_password_reset_token(
        data: PasswordResetRequestSchema,
        db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """
    Endpoint to request a password reset token.

    If the user exists and is active, invalidates any
    existing password reset tokens and generates a new one.

    Always responds with a success message to avoid leaking user information.

    Args:
        data (PasswordResetRequestSchema):
        The request data containing the user's email.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: A success message indicating
        that instructions will be sent.
    """
    stmt = select(User).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will "
                    "receive an email with instructions."
        )

    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )

    reset_token = PasswordResetToken(user_id=cast(int, user.id))
    db.add(reset_token)
    await db.commit()

    return MessageResponseSchema(
        message="If you are registered, you will "
                "receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
    summary="Reset User Password",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": (
                "Bad Request - The provided email or token is invalid, "
                "the token has expired, or the user account is not active."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid Email or Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        },
                        "expired_token": {
                            "summary": "Expired Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
                           "An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while "
                                  "resetting the password."
                    }
                }
            },
        },
    },
)
async def reset_password(
        data: PasswordResetCompleteRequestSchema,
        db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """
    Endpoint for resetting a user's password.

    Validates the token and updates the user's
    password if the token is valid and not expired.

    Deletes the token after a successful password reset.

    Args:
        data (PasswordResetCompleteRequestSchema):
        The request data containing the user's email,
         token, and new password.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: A response message indicating
        successful password reset.

    Raises:
        HTTPException:
            - 400 Bad Request if the email or token is
            invalid, or the token has expired.
            - 500 Internal Server Error if an error
            occurs during the password reset process.
    """
    stmt = select(User).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    stmt = select(PasswordResetToken).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record or token_record.token != data.token:
        if token_record:
            await db.run_sync(lambda s: s.delete(token_record))
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    expires_at = cast(
        datetime,
        token_record.expires_at
    ).replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    try:
        user.password = data.password
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )

    return MessageResponseSchema(message="Password reset successfully.")
