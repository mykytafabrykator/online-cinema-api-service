from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, Optional


class JWTAuthManagerInterface(ABC):
    """
    Interface for JWT Authentication Manager.
    Defines methods for creating, decoding, and verifying JWT tokens.
    """

    @abstractmethod
    def create_access_token(
        self, data: Dict[str, str], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new access token.

        Args:
            data (Dict[str, str]): The payload data.
            expires_delta (Optional[timedelta]): Expiry duration for the token.

        Returns:
            str: The generated access token.

        Raises:
            ValueError: If token generation fails.
        """
        pass

    @abstractmethod
    def create_refresh_token(
        self, data: Dict[str, str], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new refresh token.

        Args:
            data (Dict[str, str]): The payload data.
            expires_delta (Optional[timedelta]): Expiry duration for the token.

        Returns:
            str: The generated refresh token.

        Raises:
            ValueError: If token generation fails.
        """
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> Dict[str, str]:
        """
        Decode and validate an access token.

        Args:
            token (str): The access token.

        Returns:
            Dict[str, str]: The decoded payload.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
        """
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> Dict[str, str]:
        """
        Decode and validate a refresh token.

        Args:
            token (str): The refresh token.

        Returns:
            Dict[str, str]: The decoded payload.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
        """
        pass

    @abstractmethod
    def verify_refresh_token_or_raise(self, token: str) -> None:
        """
        Verify a refresh token or raise an error if invalid.

        Args:
            token (str): The refresh token to verify.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
        """
        pass

    @abstractmethod
    def verify_access_token_or_raise(self, token: str) -> None:
        """
        Verify an access token or raise an error if invalid.

        Args:
            token (str): The access token to verify.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
        """
        pass
