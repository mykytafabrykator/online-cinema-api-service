from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_jwt_auth_manager
from database import get_db
from database.crud.accounts import get_user_by_id
from security import JWTAuthManagerInterface
from security.http import get_token


async def get_current_user(
    token: str = Depends(get_token),
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    """
    Decode token and get current user
    """
    try:
        token_data = jwt_manager.decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
        )

    user_id = token_data.get("user_id")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with the given ID was not found.",
        )

    return user
