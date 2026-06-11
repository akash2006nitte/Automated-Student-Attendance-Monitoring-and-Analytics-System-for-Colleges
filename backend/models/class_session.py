from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional
from uuid import UUID


class ClassSessionBase(BaseModel):
    subject_id: UUID
    teacher_id: UUID
    date: date
    start_time: time
    end_time: time
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: int = 100
    qr_token: Optional[str] = None
    qr_expires_at: Optional[datetime] = None
    status: str = "scheduled"


class ClassSessionCreate(ClassSessionBase):
    pass


class ClassSessionUpdate(BaseModel):
    status: Optional[str] = None
    qr_token: Optional[str] = None
    qr_expires_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: Optional[int] = None


class ClassSession(ClassSessionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
