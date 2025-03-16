from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    get_jwt_auth_manager,
    get_settings,
    BaseAppSettings,
    get_accounts_email_notificator
)
from database import (
    get_db,
    UserGroupEnum,
)
from database.crud.accounts import (
    create_password_reset_token_by_user_id,
    create_refresh_token_by_user_id_days_token,
    create_user_by_email_password_group_id,
    create_user_group_by_name,
    db_rollback,
    delete_password_reset_token_by_user_id,
    delete_token,
    get_activation_token_by_email_token,
    get_password_reset_token_by_user_id,
    get_refresh_token_by_refresh_token,
    get_user_by_email,
    get_user_by_id,
    get_user_group_by_name,
    create_activation_token_by_user_id,
    get_latest_activation_token_by_email,
)
from exceptions import BaseSecurityError
from notifications import EmailSenderInterface
from schemas import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    MessageResponseSchema,
    UserActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    UserLoginResponseSchema,
    UserLoginRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
)
from security import JWTAuthManagerInterface

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
        email_sender: EmailSenderInterface = Depends(
            get_accounts_email_notificator
        ),
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
        email_sender (EmailSenderInterface): The asynchronous email sender.

    Returns:
        UserRegistrationResponseSchema: The newly created user's details.

    Raises:
        HTTPException:
            - 409 Conflict if a user with the same email exists.
            - 500 Internal Server Error
            if an error occurs during user creation.
    """
    existing_user = await get_user_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )

    user_group = await get_user_group_by_name(db=db, name=UserGroupEnum.USER)
    if not user_group:
        user_group = await create_user_group_by_name(
            db=db,
            name=UserGroupEnum.USER
        )

    try:
        new_user, activation_token = await (
            create_user_by_email_password_group_id(
                db=db,
                email=user_data.email,
                password=user_data.password,
                group_id=user_group.id
            )
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e
    else:
        activation_link = "http://127.0.0.1/accounts/activate/"

        await email_sender.send_activation_email(
            new_user.email,
            activation_token.token,
            activation_link,
        )

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
        email_sender: EmailSenderInterface = Depends(
            get_accounts_email_notificator
        ),
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
        email_sender (EmailSenderInterface): The asynchronous email sender.

    Returns:
        MessageResponseSchema: A response message
        confirming successful activation.

    Raises:
        HTTPException:
            - 400 Bad Request if the activation token is invalid or expired.
            - 400 Bad Request if the user account is already active.
    """
    token_record = await get_activation_token_by_email_token(
        db=db,
        email=activation_data.email,
        token=activation_data.token
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    now_utc = datetime.now(timezone.utc)
    if token_record.expires_at.replace(tzinfo=timezone.utc) < now_utc:
        await delete_token(db=db, token=token_record)
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
    await delete_token(db=db, token=token_record)

    login_link = "http://127.0.0.1/accounts/login/"

    await email_sender.send_activation_complete_email(
        str(activation_data.email),
        login_link
    )

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
        email_sender: EmailSenderInterface = Depends(
            get_accounts_email_notificator
        ),
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
        email_sender (EmailSenderInterface): The asynchronous email sender.

    Returns:
        MessageResponseSchema: A success message indicating
        that instructions will be sent.
    """
    user = await get_user_by_email(db=db, email=data.email)

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will "
                    "receive an email with instructions."
        )

    await delete_password_reset_token_by_user_id(db=db, user_id=user.id)

    await create_password_reset_token_by_user_id(db=db, user_id=user.id)

    password_reset_complete_link = ("http://127.0.0.1/"
                                    "accounts/password-reset-complete/")

    await email_sender.send_password_reset_email(
        str(data.email),
        password_reset_complete_link
    )

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
        email_sender: EmailSenderInterface = Depends(
            get_accounts_email_notificator
        ),
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
        email_sender (EmailSenderInterface): The asynchronous email sender.

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
    user = await get_user_by_email(db=db, email=data.email)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    token_record = await get_password_reset_token_by_user_id(
        db=db,
        user_id=user.id
    )

    if not token_record or token_record.token != data.token:
        if token_record:
            await delete_token(db=db, token=token_record)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    if (token_record.expires_at.replace(tzinfo=timezone.utc)
            < datetime.now(timezone.utc)):
        await delete_token(db=db, token=token_record)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    try:
        user.password = data.password
        await delete_token(db=db, token=token_record)
    except SQLAlchemyError:
        await db_rollback(db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )

    login_link = "http://127.0.0.1/accounts/login/"

    await email_sender.send_password_reset_complete_email(
        str(data.email),
        login_link
    )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password."
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is not activated."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
                           "An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while "
                                  "processing the request."
                    }
                }
            },
        },
    },
)
async def login_user(
        login_data: UserLoginRequestSchema,
        db: AsyncSession = Depends(get_db),
        settings: BaseAppSettings = Depends(get_settings),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:
    """
    Endpoint for user login.

    Authenticates a user using their email and password.
    If authentication is successful, creates a new refresh
    token and returns both access and refresh tokens.

    Args:
        login_data (UserLoginRequestSchema): The login credentials.
        db (AsyncSession): The asynchronous database session.
        settings (BaseAppSettings): The application settings.
        jwt_manager (JWTAuthManagerInterface): The JWT authentication manager.

    Returns:
        UserLoginResponseSchema: A response containing
        the access and refresh tokens.

    Raises:
        HTTPException:
            - 401 Unauthorized if the email or password is invalid.
            - 403 Forbidden if the user account is not activated.
            - 500 Internal Server Error if an error occurs
            during token creation.
    """
    user = await get_user_by_email(db=db, email=login_data.email)

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        await create_refresh_token_by_user_id_days_token(
            db=db,
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    description="Refresh the access token using a valid refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - "
                           "The provided refresh token is invalid or expired.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Token has expired."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Refresh token not found."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The user associated with "
                           "the token does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            },
        },
    },
)
async def refresh_access_token(
        token_data: TokenRefreshRequestSchema,
        db: AsyncSession = Depends(get_db),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> TokenRefreshResponseSchema:
    """
    Endpoint to refresh an access token.

    Validates the provided refresh token,
    extracts the user ID from it, and issues
    a new access token. If the token is invalid or expired,
    an error is returned.

    Args:
        token_data (TokenRefreshRequestSchema): Contains the refresh token.
        db (AsyncSession): The asynchronous database session.
        jwt_manager (JWTAuthManagerInterface): JWT authentication manager.

    Returns:
        TokenRefreshResponseSchema: A new access token.

    Raises:
        HTTPException:
            - 400 Bad Request if the token is invalid or expired.
            - 401 Unauthorized if the refresh token is not found.
            - 404 Not Found if the user associated with the token
             does not exist.
    """
    try:
        decoded_token = jwt_manager.decode_refresh_token(
            token_data.refresh_token
        )
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    refresh_token_record = await get_refresh_token_by_refresh_token(
        db,
        token_data.refresh_token
    )
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})

    return TokenRefreshResponseSchema(access_token=new_access_token)


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
    summary="User Logout",
    description="Logout user by invalidating the refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "Unauthorized - Invalid or missing refresh token.",
            "content": {
                "application/json": {
                    "example": {"detail": "Refresh token not found."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred "
                                          "while processing the request."}
                }
            },
        },
    },
)
async def logout_user(
        token_data: TokenRefreshRequestSchema,
        db: AsyncSession = Depends(get_db),
) -> MessageResponseSchema:
    """
    Endpoint to logout a user by deleting the refresh token.

    Args:
        token_data (TokenRefreshRequestSchema): Contains the refresh token.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: Confirmation message.

    Raises:
        HTTPException:
            - 401 Unauthorized if the refresh token is invalid.
            - 500 Internal Server Error if an issue occurs during deletion.
    """
    refresh_token_record = await get_refresh_token_by_refresh_token(
        db=db, refresh_token=token_data.refresh_token
    )

    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found."
        )

    try:
        await delete_token(db=db, token=refresh_token_record)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )

    return MessageResponseSchema(message="User logged out successfully.")


@router.post(
    "/resend-activation/",
    response_model=MessageResponseSchema,
    summary="Resend Activation Email",
    description="Resend a new activation token if the previous one expired.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - User is already active.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is already active."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - User with this email does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User with this email does not exist."
                    }
                }
            },
        },
    },
)
async def resend_activation_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(
        get_accounts_email_notificator
    ),
) -> MessageResponseSchema:
    """
    Endpoint for resending the activation email.

    Checks if the user exists and is not activated.
    Deletes the old activation token and generates a new one.
    Sends an activation email with a new token.

    Args:
        email (str): The user's email address.
        db (AsyncSession): The asynchronous database session.
        email_sender (EmailSenderInterface): The email sender service.

    Returns:
        MessageResponseSchema: A success message confirming the email was sent.

    Raises:
        HTTPException:
            - 400 Bad Request if the user is already active.
            - 404 Not Found if the user does not exist.
    """
    user = await get_user_by_email(db=db, email=email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist."
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    token_record = await get_latest_activation_token_by_email(
        db=db,
        email=email
    )
    if token_record:
        await delete_token(db=db, token=token_record)

    new_activation_token = await create_activation_token_by_user_id(
        db=db,
        user_id=user.id
    )

    activation_link = "http://127.0.0.1/accounts/activate/"
    await email_sender.send_activation_email(
        user.email,
        new_activation_token.token,
        activation_link
    )

    return MessageResponseSchema(
        message="New activation email sent successfully."
    )
