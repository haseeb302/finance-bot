from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.settings import settings
from app.services.storage_dynamodb import storage_service

# Password hashing - support both bcrypt (legacy) and Argon2 (new)
# This allows verification of existing bcrypt hashes while using Argon2 for new passwords
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2."""
    # Always use Argon2 for new password hashes
    return pwd_context.hash(password, scheme="argon2")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.refresh_token_expire_minutes
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user."""
    try:
        token = credentials.credentials
        print(f"Verifying token: {token[:50]}...")
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        print(f"Token payload user_id: {user_id}")

        if user_id is None:
            print("No user_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        user = await storage_service.get_user_by_id(user_id)
        if user is None:
            print(f"User not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.get("is_active", True):
            print(f"User {user_id} is inactive")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        print(f"Successfully authenticated user: {user_id}")
        return user
    except Exception as e:
        print(f"Error in get_current_user: {str(e)}")
        raise


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get current active user."""
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    return await get_current_user_optional_from_session(credentials)


# Session-based authentication functions
async def get_current_user_from_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from session."""
    try:
        token = credentials.credentials
        print(f"Verifying session token: {token[:50]}...")

        # First verify the token
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        print(f"Token payload user_id: {user_id}")

        if user_id is None:
            print("No user_id in token payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        # Get user from database
        user = await storage_service.get_user_by_id(user_id)
        if user is None:
            print(f"User not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.get("is_active", True):
            print(f"User {user_id} is inactive")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        print(f"Successfully authenticated user from session: {user_id}")
        return user
    except Exception as e:
        print(f"Error in get_current_user_from_session: {str(e)}")
        raise


async def get_current_user_optional_from_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """Get current user if authenticated via session, otherwise return None.

    This function properly handles session expiry and will return None when:
    - No credentials provided
    - Token is expired or invalid
    - User not found or inactive
    - Any other authentication error

    The frontend should handle None responses by logging out the user.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        user_id = payload.get("sub")

        if user_id is None:
            print("No user_id in token payload")
            return None

        user = await storage_service.get_user_by_id(user_id)
        if user is None:
            print(f"User not found for user_id: {user_id}")
            return None

        if not user.get("is_active", True):
            print(f"User {user_id} is inactive")
            return None

        return user
    except HTTPException as e:
        # Token is expired, invalid, or malformed - user should be logged out
        print(f"Session validation failed: {e.detail}")
        return None
    except Exception as e:
        # Log unexpected errors but don't expose them to client
        print(f"Unexpected error in session validation: {str(e)}")
        return None
