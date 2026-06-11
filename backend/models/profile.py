from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    roll_number: Optional[str] = None
    photo_url: Optional[str] = None


class ProfileCreate(ProfileBase):
    id: UUID
    full_name: str
    role: str


class ProfileUpdate(ProfileBase):
    pass


class Profile(ProfileBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
