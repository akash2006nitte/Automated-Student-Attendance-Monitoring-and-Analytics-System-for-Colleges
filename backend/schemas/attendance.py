from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional, List
from uuid import UUID


class SessionCreate(BaseModel):
    subject_id: UUID
    date: date
    start_time: time
    end_time: time
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: int = 100


class SessionResponse(BaseModel):
    id: UUID
    subject_id: UUID
    subject_name: Optional[str] = None
    teacher_id: UUID
    teacher_name: Optional[str] = None
    date: date
    start_time: time
    end_time: time
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: int
    qr_token: Optional[str] = None
    qr_expires_at: Optional[datetime] = None
    status: str
    created_at: datetime


class QRMarkRequest(BaseModel):
    session_id: UUID
    qr_token: str
    latitude: float
    longitude: float
    device_info: Optional[str] = None


class ManualMarkRequest(BaseModel):
    session_id: UUID
    student_id: UUID
    status: str


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    student_id: UUID
    student_name: Optional[str] = None
    student_roll_number: Optional[str] = None
    subject_id: UUID
    status: str
    marked_at: Optional[datetime] = None
    method: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AttendanceSummary(BaseModel):
    subject_id: UUID
    subject_name: str
    total_classes: int
    present: int
    absent: int
    late: int
    excused: int
    percentage: float


class SubjectAnalytics(BaseModel):
    subject_id: UUID
    subject_name: str
    total_students: int
    average_attendance: float
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
