from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import Response
from supabase import Client
import os
from datetime import datetime
from dotenv import load_dotenv

from schemas.attendance import (
    SessionCreate, SessionResponse, QRMarkRequest, ManualMarkRequest,
    AttendanceRecordResponse, AttendanceSummary, SubjectAnalytics
)
from services.qr_service import QRService
from services.geo_service import GeoService
from services.analytics_service import AnalyticsService

load_dotenv()

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()
qr_service = QRService()
geo_service = GeoService()
analytics_service = AnalyticsService()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, current_user: dict = Depends(lambda: {})):
    """Create a new class session (teacher only)"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create sessions"
        )
    
    try:
        # Get subject info
        subject = supabase.table("subjects").select("*").eq("id", session_data.subject_id).single().execute()
        if not subject.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found"
            )
        
        session_payload = {
            "subject_id": session_data.subject_id,
            "teacher_id": current_user["id"],
            "date": session_data.date.isoformat(),
            "start_time": session_data.start_time.isoformat(),
            "end_time": session_data.end_time.isoformat(),
            "latitude": session_data.latitude,
            "longitude": session_data.longitude,
            "geofence_radius": session_data.geofence_radius,
            "status": "scheduled"
        }
        
        result = supabase.table("class_sessions").insert(session_payload).execute()
        session = result.data[0] if result.data else None
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        return SessionResponse(
            id=session["id"],
            subject_id=session["subject_id"],
            subject_name=subject.data["name"],
            teacher_id=session["teacher_id"],
            teacher_name=current_user.get("full_name"),
            date=session["date"],
            start_time=session["start_time"],
            end_time=session["end_time"],
            latitude=session["latitude"],
            longitude=session["longitude"],
            geofence_radius=session["geofence_radius"],
            qr_token=session["qr_token"],
            qr_expires_at=session["qr_expires_at"],
            status=session["status"],
            created_at=session["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


@router.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start_session(session_id: str, current_user: dict = Depends(lambda: {})):
    """Start a session and generate QR token"""
    try:
        # Get session
        session = supabase.table("class_sessions").select("*").eq("id", session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.data["teacher_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only start your own sessions"
            )
        
        # Generate QR token
        qr_token = qr_service.generate_token()
        qr_expires_at = qr_service.get_expiration_time()
        
        # Update session
        update_data = {
            "qr_token": qr_token,
            "qr_expires_at": qr_expires_at.isoformat(),
            "status": "ongoing"
        }
        
        result = supabase.table("class_sessions").update(update_data).eq("id", session_id).execute()
        updated_session = result.data[0] if result.data else None
        
        # Get subject name
        subject = supabase.table("subjects").select("name").eq("id", updated_session["subject_id"]).single().execute()
        
        return SessionResponse(
            id=updated_session["id"],
            subject_id=updated_session["subject_id"],
            subject_name=subject.data["name"] if subject.data else None,
            teacher_id=updated_session["teacher_id"],
            teacher_name=current_user.get("full_name"),
            date=updated_session["date"],
            start_time=updated_session["start_time"],
            end_time=updated_session["end_time"],
            latitude=updated_session["latitude"],
            longitude=updated_session["longitude"],
            geofence_radius=updated_session["geofence_radius"],
            qr_token=updated_session["qr_token"],
            qr_expires_at=updated_session["qr_expires_at"],
            status=updated_session["status"],
            created_at=updated_session["created_at"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting session: {str(e)}"
        )


@router.get("/sessions/{session_id}/qr")
async def get_qr_code(session_id: str, current_user: dict = Depends(lambda: {})):
    """Get QR code for a session"""
    try:
        session = supabase.table("class_sessions").select("*").eq("id", session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if not session.data["qr_token"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR token not generated. Start the session first."
            )
        
        # Generate QR code image
        qr_image = qr_service.generate_qr_code(session.data["qr_token"])
        
        return Response(content=qr_image, media_type="image/png")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating QR code: {str(e)}"
        )


@router.post("/mark/qr")
async def mark_attendance_qr(request: QRMarkRequest, current_user: dict = Depends(lambda: {})):
    """Student marks attendance using QR code"""
    try:
        # Get session
        session = supabase.table("class_sessions").select("*").eq("id", request.session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Validate QR token
        is_valid, error_msg = qr_service.validate_token(
            request.qr_token,
            session.data["qr_token"],
            session.data["qr_expires_at"]
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check geofence
        if session.data["latitude"] and session.data["longitude"]:
            is_within, distance = geo_service.is_within_geofence(
                request.latitude,
                request.longitude,
                session.data["latitude"],
                session.data["longitude"],
                session.data["geofence_radius"]
            )
            
            if not is_within:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You are outside the geofence. Distance: {distance:.2f}m"
                )
        
        # Check if already marked
        existing = supabase.table("attendance_records").select("*").eq(
            "session_id", request.session_id
        ).eq("student_id", current_user["id"]).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attendance already marked for this session"
            )
        
        # Get subject info
        subject = supabase.table("subjects").select("*").eq("id", session.data["subject_id"]).single().execute()
        
        # Mark attendance
        attendance_data = {
            "session_id": request.session_id,
            "student_id": current_user["id"],
            "subject_id": session.data["subject_id"],
            "status": "present",
            "marked_at": datetime.utcnow().isoformat(),
            "method": "qr",
            "latitude": request.latitude,
            "longitude": request.longitude,
            "device_info": request.device_info
        }
        
        result = supabase.table("attendance_records").insert(attendance_data).execute()
        
        return {"message": "Attendance marked successfully", "status": "present"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking attendance: {str(e)}"
        )


@router.post("/mark/manual")
async def mark_attendance_manual(request: ManualMarkRequest, current_user: dict = Depends(lambda: {})):
    """Teacher manually marks student attendance"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can manually mark attendance"
        )
    
    try:
        # Get session
        session = supabase.table("class_sessions").select("*").eq("id", request.session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.data["teacher_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only mark attendance for your sessions"
            )
        
        # Check if already marked
        existing = supabase.table("attendance_records").select("*").eq(
            "session_id", request.session_id
        ).eq("student_id", request.student_id).execute()
        
        if existing.data:
            # Update existing
            result = supabase.table("attendance_records").update({
                "status": request.status,
                "marked_at": datetime.utcnow().isoformat(),
                "method": "manual"
            }).eq("id", existing.data[0]["id"]).execute()
        else:
            # Create new
            attendance_data = {
                "session_id": request.session_id,
                "student_id": request.student_id,
                "subject_id": session.data["subject_id"],
                "status": request.status,
                "marked_at": datetime.utcnow().isoformat(),
                "method": "manual"
            }
            result = supabase.table("attendance_records").insert(attendance_data).execute()
        
        return {"message": "Attendance marked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking attendance: {str(e)}"
        )


@router.get("/sessions/{session_id}/records", response_model=list[AttendanceRecordResponse])
async def get_session_attendance(session_id: str, current_user: dict = Depends(lambda: {})):
    """Get all attendance records for a session"""
    try:
        # Get session
        session = supabase.table("class_sessions").select("*").eq("id", session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Check permissions
        if (session.data["teacher_id"] != current_user["id"] and 
            current_user.get("role") != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get attendance records with student info
        records = supabase.table("attendance_records").select(
            "*"
        ).eq("session_id", session_id).execute()
        
        result = []
        for record in records.data:
            # Get student info
            student = supabase.table("profiles").select(
                "full_name", "roll_number"
            ).eq("id", record["student_id"]).single().execute()
            
            # Get subject info
            subject = supabase.table("subjects").select("name").eq("id", record["subject_id"]).single().execute()
            
            result.append(AttendanceRecordResponse(
                id=record["id"],
                session_id=record["session_id"],
                student_id=record["student_id"],
                student_name=student.data.get("full_name") if student.data else None,
                student_roll_number=student.data.get("roll_number") if student.data else None,
                subject_id=record["subject_id"],
                status=record["status"],
                marked_at=record["marked_at"],
                method=record["method"],
                latitude=record["latitude"],
                longitude=record["longitude"]
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching attendance: {str(e)}"
        )


@router.get("/student/{student_id}/summary", response_model=list[AttendanceSummary])
async def get_student_attendance_summary(student_id: str, current_user: dict = Depends(lambda: {})):
    """Get per-subject attendance summary for a student"""
    try:
        # Check permissions
        if current_user["id"] != student_id and current_user.get("role") not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get all attendance records for student
        records = supabase.table("attendance_records").select("*").eq("student_id", student_id).execute()
        
        # Group by subject
        subject_records = {}
        for record in records.data:
            subject_id = record["subject_id"]
            if subject_id not in subject_records:
                subject_records[subject_id] = []
            subject_records[subject_id].append(record)
        
        # Calculate summary for each subject
        summaries = []
        for subject_id, subj_records in subject_records.items():
            subject = supabase.table("subjects").select("name").eq("id", subject_id).single().execute()
            summary_data = analytics_service.get_student_attendance_summary(subj_records)
            
            summaries.append(AttendanceSummary(
                subject_id=subject_id,
                subject_name=subject.data["name"] if subject.data else "Unknown",
                **summary_data
            ))
        
        return summaries
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching summary: {str(e)}"
        )


@router.get("/subject/{subject_id}/analytics", response_model=SubjectAnalytics)
async def get_subject_analytics(subject_id: str, current_user: dict = Depends(lambda: {})):
    """Get full analytics for a subject"""
    try:
        # Get subject
        subject = supabase.table("subjects").select("*").eq("id", subject_id).single().execute()
        if not subject.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found"
            )
        
        # Check permissions
        if (subject.data["teacher_id"] != current_user["id"] and 
            current_user.get("role") != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get all attendance records for subject
        records = supabase.table("attendance_records").select("*").eq("subject_id", subject_id).execute()
        
        # Calculate analytics
        total_students = len(set(r["student_id"] for r in records.data))
        present = sum(1 for r in records.data if r["status"] == "present")
        absent = sum(1 for r in records.data if r["status"] == "absent")
        late = sum(1 for r in records.data if r["status"] == "late")
        excused = sum(1 for r in records.data if r["status"] == "excused")
        
        total = len(records.data)
        average_attendance = analytics_service.calculate_attendance_percentage(total, present + late)
        
        return SubjectAnalytics(
            subject_id=subject_id,
            subject_name=subject.data["name"],
            total_students=total_students,
            average_attendance=average_attendance,
            present_count=present,
            absent_count=absent,
            late_count=late,
            excused_count=excused
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching analytics: {str(e)}"
        )


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, current_user: dict = Depends(lambda: {})):
    """End a session and mark it as completed"""
    try:
        session = supabase.table("class_sessions").select("*").eq("id", session_id).single().execute()
        if not session.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.data["teacher_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only end your own sessions"
            )
        
        # Update session status
        result = supabase.table("class_sessions").update({
            "status": "completed",
            "qr_token": None,
            "qr_expires_at": None
        }).eq("id", session_id).execute()
        
        return {"message": "Session ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
        )
