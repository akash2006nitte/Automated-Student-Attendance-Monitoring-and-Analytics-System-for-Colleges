from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
from uuid import UUID


class LeaveRequestBase(BaseModel):
    student_id: UUID
    subject_id: UUID
    from_date: date
    to_date: date
    reason: str
    document_url: Optional[str] = None
    status: str = "pending"
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None


class LeaveRequestCreate(BaseModel):
    subject_id: UUID
    from_date: date
    to_date: date
    reason: str
    document_url: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    status: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None


class LeaveRequest(LeaveRequestBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
