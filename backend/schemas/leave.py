from pydantic import BaseModel
from datetime import date
from typing import Optional
from uuid import UUID


class LeaveRequestCreate(BaseModel):
    subject_id: UUID
    from_date: date
    to_date: date
    reason: str
    document_url: Optional[str] = None


class LeaveReview(BaseModel):
    status: str


class LeaveRequestResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_name: Optional[str] = None
    subject_id: UUID
    subject_name: Optional[str] = None
    from_date: date
    to_date: date
    reason: str
    document_url: Optional[str] = None
    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
