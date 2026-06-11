from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = Field(..., pattern="^(admin|teacher|student)$")
    department: Optional[str] = None
    semester: Optional[int] = None
    roll_number: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    semester: Optional[int] = None
    roll_number: Optional[str] = None
    photo_url: Optional[str] = None
