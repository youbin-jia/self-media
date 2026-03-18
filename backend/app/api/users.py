# backend/app/api/users.py
"""User management API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserUpdate, UserRoleUpdate, MessageResponse
from app.middleware.auth import get_current_user, require_roles

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = require_roles(["admin"])
):
    """
    List all users.

    Admin only endpoint to retrieve all registered users.
    """
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user by ID.

    Users can only view their own profile unless they are admin.
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user information.

    Users can only update their own profile unless they are admin.
    """
    # Check permissions
    if current_user.id != user_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields if provided
    if update_data.username is not None:
        # Check if new username is already taken
        existing = db.query(User).filter(
            User.username == update_data.username,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        user.username = update_data.username

    if update_data.email is not None:
        # Check if new email is already taken
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = update_data.email

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = require_roles(["admin"])
):
    """
    Delete user.

    Admin only endpoint to remove a user account.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return MessageResponse(message="User deleted successfully")


@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = require_roles(["admin"])
):
    """
    Update user role.

    Admin only endpoint to change a user's role.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from demoting themselves
    if user.id == current_user.id and role_data.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    user.role = role_data.role
    db.commit()
    db.refresh(user)

    return user
