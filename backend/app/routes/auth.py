from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from datetime import datetime

from app.schemas.auth import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    SessionCreate,
    SessionResponse,
    SessionListResponse,
)
from app.services.storage_dynamodb import storage_service
from app.utils.auth import (
    get_password_hash,
    verify_token,
    get_current_active_user,
)
from app.core.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/signin", response_model=TokenResponse)
async def signin(login_data: LoginRequest):
    """Unified signin endpoint - creates account if user doesn't exist, otherwise logs in."""
    try:
        # Check if user exists
        user = await storage_service.get_user_by_email(login_data.email)

        if user:
            # User exists - verify password and login
            from app.utils.auth import verify_password

            if not verify_password(login_data.password, user["hashed_password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password",
                )

            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account is inactive",
                )
        else:
            # User doesn't exist - create new account
            from app.schemas.auth import UserCreate

            # Generate username from email (part before @)
            username = login_data.email.split("@")[0]

            # Create user data
            user_data = UserCreate(
                email=login_data.email,
                username=username,
                full_name=username,  # Use username as full name initially
                password=login_data.password,
            )

            # Hash password
            hashed_password = get_password_hash(login_data.password)

            # Create user
            user = await storage_service.create_user(user_data, hashed_password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create account",
                )

        # Update last login
        await storage_service.db.update_user(
            user["user_id"], {"last_login": datetime.utcnow().isoformat()}
        )

        # Create tokens
        from app.utils.auth import create_access_token, create_refresh_token
        from datetime import timedelta

        access_token = create_access_token(data={"sub": user["user_id"]})
        refresh_token = create_refresh_token(data={"sub": user["user_id"]})

        # Debug logging
        print(f"Created tokens for user {user['user_id']}")
        print(f"Access token: {access_token[:50]}...")

        # Create session
        session_data = SessionCreate(
            user_id=user["user_id"],
            access_token=access_token,
            refresh_token=refresh_token,
            device_info=None,  # Could be extracted from request headers
            ip_address=None,  # Could be extracted from request
        )

        # Use refresh token expiry for session expiry to keep them in sync
        expires_at = (
            datetime.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)
        ).isoformat()
        session = await storage_service.create_session(session_data, expires_at)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session",
            )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes
            * 60,  # Convert minutes to seconds
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 401, 400, etc.)
        raise
    except Exception as e:
        # Log unexpected errors and return 500
        print(f"Unexpected error in signin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    print(f"Refresh token request received: {refresh_data.refresh_token[:20]}...")

    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token, "refresh")
    user_id = payload.get("sub")
    exp_time = payload.get("exp")
    print(f"Refresh token payload user_id: {user_id}")
    print(f"Refresh token expires at: {datetime.fromtimestamp(exp_time).isoformat()}")
    print(f"Current time: {datetime.utcnow().isoformat()}")
    print(f"Token expired: {datetime.fromtimestamp(exp_time) < datetime.utcnow()}")

    if not user_id:
        print("No user_id in refresh token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Check if refresh token exists in database
    print("Checking refresh token in database...")
    refresh_token_obj = await storage_service.get_refresh_token(
        refresh_data.refresh_token
    )
    if not refresh_token_obj:
        print("Refresh token not found in database - this is the issue!")
        print(f"Looking for token: {refresh_data.refresh_token[:50]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    print(f"Refresh token found in database: {refresh_token_obj.get('session_id')}")

    # Get user
    user = await storage_service.get_user_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token only (don't renew refresh token)
    from app.utils.auth import create_access_token
    from datetime import timedelta

    access_token = create_access_token(data={"sub": user_id})

    # Keep the same refresh token and session expiry
    # The refresh token should expire based on its original creation time
    print(f"Refresh token will expire at: {refresh_token_obj.get('expires_at')}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Return the same refresh token
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes
        * 60,  # Convert minutes to seconds
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_active_user)):
    """Logout user by invalidating current session."""
    try:
        # Get the current session from the token
        # For now, we'll invalidate all sessions for the user
        success = await storage_service.invalidate_user_sessions(
            current_user["user_id"]
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout",
            )

        return {"message": "Successfully logged out"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information."""
    print(f"/auth/me endpoint called for user: {current_user.get('user_id')}")
    return UserResponse(
        id=current_user["user_id"],
        email=current_user["email"],
        username=current_user.get("username"),
        full_name=current_user.get("full_name"),
        is_active=current_user.get("is_active", True),
        is_verified=current_user.get("is_verified", False),
        created_at=current_user["created_at"],
        updated_at=current_user.get("updated_at"),
        last_login=current_user.get("last_login"),
    )


@router.post("/forgot-password")
async def forgot_password(reset_data: PasswordResetRequest):
    """Send password reset email."""
    # Check if user exists
    user = await storage_service.get_user_by_email(reset_data.email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    """Reset password with token."""
    return {"message": "Password reset functionality not implemented yet"}


# Session Management Endpoints
@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(current_user: dict = Depends(get_current_active_user)):
    """Get all active sessions for the current user."""
    try:
        sessions = await storage_service.get_user_sessions(
            current_user["user_id"], active_only=True
        )

        # Convert to response format
        session_responses = []
        for session in sessions:
            session_responses.append(
                SessionResponse(
                    session_id=session["session_id"],
                    user_id=session["user_id"],
                    access_token=session["access_token"],
                    refresh_token=session["refresh_token"],
                    is_active=session["is_active"],
                    created_at=datetime.fromisoformat(session["created_at"]),
                    expires_at=datetime.fromisoformat(session["expires_at"]),
                    last_activity=(
                        datetime.fromisoformat(session["last_activity"])
                        if session.get("last_activity")
                        else None
                    ),
                    device_info=session.get("device_info"),
                    ip_address=session.get("ip_address"),
                )
            )

        return SessionListResponse(
            sessions=session_responses, total=len(session_responses)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, current_user: dict = Depends(get_current_active_user)
):
    """Delete a specific session."""
    try:
        # Verify the session belongs to the current user
        session = await storage_service.get_session(session_id)
        if not session or session["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        success = await storage_service.delete_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session",
            )

        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


@router.delete("/sessions/all")
async def delete_all_sessions(current_user: dict = Depends(get_current_active_user)):
    """Delete all sessions for the current user."""
    try:
        success = await storage_service.invalidate_user_sessions(
            current_user["user_id"]
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete all sessions",
            )

        return {"message": "All sessions deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all sessions: {str(e)}",
        )
