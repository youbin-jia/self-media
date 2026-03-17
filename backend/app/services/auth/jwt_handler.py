# backend/app/services/auth/jwt_handler.py
"""JWT Handler for token-based authentication"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from app.config import settings


class JWTHandler:
    """Handles JWT token creation and validation"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        expire_hours: Optional[int] = None
    ):
        """
        Initialize JWT handler.

        Args:
            secret_key: JWT secret key (defaults to settings)
            algorithm: JWT algorithm (defaults to settings)
            expire_hours: Token expiration time in hours (defaults to settings)
        """
        self.secret_key = secret_key or settings.JWT_SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.expire_hours = expire_hours or settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS

    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User's unique identifier (UUID)
            username: User's username
            role: User's role (admin, editor, viewer)
            expires_delta: Optional custom expiration timedelta

        Returns:
            Encoded JWT token string
        """
        now = datetime.utcnow()

        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(hours=self.expire_hours)

        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": expire,
            "iat": now
        }

        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dictionary if valid, None if invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid (wrong signature, malformed, etc.)
            return None
