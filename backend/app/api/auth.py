# backend/app/api/auth.py
"""Authentication API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, MessageResponse
from app.services.auth.jwt_handler import JWTHandler
from app.middleware.auth import get_current_user

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Creates a new user account with default 'viewer' role.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user with hashed password
    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=UserRole.VIEWER.value
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login and get access token.

    Validates credentials and returns a JWT token.
    """
    # Find user by username
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not pwd_context.verify(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    jwt_handler = JWTHandler()
    access_token = jwt_handler.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )

    return Token(access_token=access_token)


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token.

    Generates a new token for the authenticated user.
    """
    jwt_handler = JWTHandler()
    access_token = jwt_handler.create_access_token(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role
    )

    return Token(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user.

    Note: With stateless JWT, actual logout is handled client-side by removing the token.
    This endpoint exists for API completeness and can be extended for token blacklisting.
    """
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information.

    Returns the authenticated user's profile.
    """
    return current_user
