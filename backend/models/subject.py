from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class SubjectBase(BaseModel):
    name: str
    code: str
    department: str
    semester: int
    teacher_id: Optional[UUID] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    teacher_id: Optional[UUID] = None


class Subject(SubjectBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
