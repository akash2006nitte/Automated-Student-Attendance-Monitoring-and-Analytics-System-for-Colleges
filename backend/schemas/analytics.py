from pydantic import BaseModel
from datetime import date
from typing import List, Optional
from uuid import UUID


class DepartmentAnalytics(BaseModel):
    department: str
    total_students: int
    average_attendance: float
    total_sessions: int
    subject_breakdown: List[dict]


class StudentTrend(BaseModel):
    student_id: UUID
    student_name: str
    monthly_data: List[dict]
    trend: str


class DefaulterAlert(BaseModel):
    student_id: UUID
    student_name: str
    roll_number: str
    department: str
    semester: int
    overall_attendance: float
    subject_breakdown: List[dict]
    trend: str


class HourlyAnalytics(BaseModel):
    subject_id: UUID
    subject_name: str
    hourly_data: List[dict]
    best_hour: Optional[str] = None
    worst_hour: Optional[str] = None
