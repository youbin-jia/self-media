# backend/app/schemas/user.py
"""Pydantic schemas for user and authentication"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user info"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None


class UserRoleUpdate(BaseModel):
    """Schema for updating user role"""
    role: str = Field(..., pattern="^(admin|editor|viewer)$")


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for access token response"""
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Schema for message response"""
    message: str
