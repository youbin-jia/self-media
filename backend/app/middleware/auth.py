# backend/app/middleware/auth.py
"""Authentication middleware for JWT token validation and role-based permission checking"""
from typing import List, Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.services.auth.jwt_handler import JWTHandler


# HTTPBearer security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to extract and validate user from JWT token.

    Extracts Bearer token from Authorization header, decodes the JWT token,
    queries user from database, and returns the User object.

    Args:
        credentials: HTTP Bearer credentials from Authorization header
        db: Database session

    Returns:
        User: The authenticated user object

    Raises:
        HTTPException: 401 if credentials are invalid, token is invalid,
                      user not found, or user is inactive
    """
    # Check if credentials are provided
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode the JWT token
    jwt_handler = JWTHandler()
    payload = jwt_handler.decode_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user_id from payload
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(roles: List[str]):
    """
    Decorator to check user roles.

    Creates a decorator that validates the current user has one of the
    allowed roles. Admin role has access to all routes.

    Args:
        roles: List of allowed role names (e.g., ["admin", "editor"])

    Returns:
        Decorator function that wraps the route handler

    Raises:
        HTTPException: 403 if user role is not in the allowed roles
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, current_user: User = None, **kwargs):
            # Get current_user from kwargs or args
            if current_user is None:
                # Try to find current_user in kwargs
                current_user = kwargs.get('current_user')

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            # Admin has access to everything
            if current_user.role == UserRole.ADMIN.value:
                return func(*args, current_user=current_user, **kwargs)

            # Check if user role is in allowed roles
            if current_user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required role: {', '.join(roles)}"
                )

            return func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def check_project_access(project_id: str, user: User, db: Session) -> bool:
    """
    Check project access permission based on user role.

    Permission rules:
    - Admin: access all projects
    - Editor: access owned projects only (owner_id matches user.id)
    - Viewer: access team member projects only (not implemented yet, returns False)

    Note: Team membership feature will be added in a future phase.
    Currently, editors can only access projects they own.

    Args:
        project_id: UUID of the project to check access for
        user: The user requesting access
        db: Database session

    Returns:
        bool: True if user has access, False otherwise
    """
    # Admin can access all projects
    if user.role == UserRole.ADMIN.value:
        return True

    # Query the project
    project = db.query(Project).filter(Project.id == project_id).first()

    if project is None:
        return False

    # Editor can access owned projects
    if user.role == UserRole.EDITOR.value:
        return project.owner_id == user.id

    # Viewer can only access team member projects (not implemented yet)
    # For now, viewers have no project access unless team membership is added
    if user.role == UserRole.VIEWER.value:
        # Future: Check team membership
        # return project.id in [p.id for p in user.team_projects]
        return False

    return False
