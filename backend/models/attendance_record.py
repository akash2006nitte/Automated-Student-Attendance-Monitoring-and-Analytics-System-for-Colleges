from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class AttendanceRecordBase(BaseModel):
    session_id: UUID
    student_id: UUID
    subject_id: UUID
    status: str = "absent"
    marked_at: Optional[datetime] = None
    method: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_info: Optional[str] = None


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordUpdate(BaseModel):
    status: Optional[str] = None
    method: Optional[str] = None
    marked_at: Optional[datetime] = None


class AttendanceRecord(AttendanceRecordBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
