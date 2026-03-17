# backend/app/middleware/auth.py
"""
Authentication middleware for JWT token validation and role-based permission checking.

Architecture Decision: Simple Role-Based Access Control
=======================================================
This module implements a simple role-based access control (RBAC) approach rather than
a full-featured RBAC system with granular permissions, resource-level policies, or
role hierarchies. This design choice was made because:

1. The application has only three roles (admin, editor, viewer) with well-defined
   permission boundaries.
2. A full RBAC system would add unnecessary complexity for the current requirements.
3. The simple approach provides clear, auditable access control without the overhead
   of permission tables, role inheritance, or policy evaluation engines.

If the application grows to require more granular permissions (e.g., per-resource
permissions, time-based access, or complex role hierarchies), this should be
migrated to a proper RBAC framework with database-backed permission models.
"""
from typing import List, Optional

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


def require_roles(roles: List[str]):
    """
    Dependency factory for role-based access control.

    Creates a FastAPI dependency that validates the current user has one of the
    allowed roles. This pattern integrates seamlessly with FastAPI's dependency
    injection system.

    Architecture Note: This simple role-checking approach is sufficient for the
    current three-role system (admin, editor, viewer). For more complex scenarios,
    consider migrating to a full RBAC system.

    Args:
        roles: List of allowed role names (e.g., ["admin", "editor"])

    Returns:
        Depends: A FastAPI dependency that returns the authenticated User if
                 they have the required role, or raises HTTPException.

    Usage:
        @router.post("/admin-only")
        async def admin_route(user: User = require_roles(["admin"])):
            return {"message": "Admin access granted"}

    Raises:
        HTTPException: 403 if user role is not in the allowed roles
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user
    return Depends(role_checker)


def check_project_access(project_id: str, user: User, db: Session) -> bool:
    """
    Check project access permission based on user role.

    Permission rules:
    - Admin: access all projects
    - Editor: access owned projects or projects where they are a team member
    - Viewer: access projects where they are a team member

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

    # Get team members list (handle None case)
    team_members = project.team_members or []

    # Editor can access owned projects or team member projects
    if user.role == UserRole.EDITOR.value:
        return (project.owner_id == user.id or
                user.id in team_members)

    # Viewer can only access team member projects
    if user.role == UserRole.VIEWER.value:
        return user.id in team_members

    return False
