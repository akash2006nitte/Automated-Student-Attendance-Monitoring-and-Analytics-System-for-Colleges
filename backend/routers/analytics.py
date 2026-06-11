from fastapi import APIRouter, HTTPException, status
from supabase import Client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from schemas.analytics import DepartmentAnalytics, StudentTrend, DefaulterAlert, HourlyAnalytics
from services.analytics_service import AnalyticsService

load_dotenv()

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/department/{department}", response_model=DepartmentAnalytics)
async def get_department_analytics(department: str, current_user: dict = Depends(lambda: {})):
    """Get department-wide attendance analytics"""
    if current_user.get("role") not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get all students in department
        students = supabase.table("profiles").select("*").eq(
            "department", department
        ).eq("role", "student").execute()
        
        total_students = len(students.data) if students.data else 0
        
        # Get all subjects in department
        subjects = supabase.table("subjects").select("*").eq("department", department).execute()
        
        # Get all attendance records for department
        subject_ids = [s["id"] for s in subjects.data] if subjects.data else []
        if not subject_ids:
            return DepartmentAnalytics(
                department=department,
                total_students=total_students,
                average_attendance=0.0,
                total_sessions=0,
                subject_breakdown=[]
            )
        
        records = supabase.table("attendance_records").select("*").in_(
            "subject_id", subject_ids
        ).execute()
        
        total_records = len(records.data) if records.data else 0
        present = sum(1 for r in records.data if r["status"] in ["present", "late"]) if records.data else 0
        average_attendance = analytics_service.calculate_attendance_percentage(total_records, present)
        
        # Subject breakdown
        subject_breakdown = []
        for subject in subjects.data:
            subject_records = [r for r in records.data if r["subject_id"] == subject["id"]] if records.data else []
            subj_present = sum(1 for r in subject_records if r["status"] in ["present", "late"])
            subj_total = len(subject_records)
            subj_percentage = analytics_service.calculate_attendance_percentage(subj_total, subj_present)
            
            subject_breakdown.append({
                "subject_name": subject["name"],
                "subject_code": subject["code"],
                "attendance_percentage": subj_percentage,
                "total_classes": subj_total
            })
        
        return DepartmentAnalytics(
            department=department,
            total_students=total_students,
            average_attendance=average_attendance,
            total_sessions=total_records,
            subject_breakdown=subject_breakdown
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching department analytics: {str(e)}"
        )


@router.get("/student/{student_id}/trend", response_model=StudentTrend)
async def get_student_trend(student_id: str, current_user: dict = Depends(lambda: {})):
    """Get monthly attendance trend for a student"""
    if current_user["id"] != student_id and current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get student info
        student = supabase.table("profiles").select("*").eq("id", student_id).single().execute()
        if not student.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Get attendance records
        records = supabase.table("attendance_records").select("*").eq("student_id", student_id).execute()
        
        # Get monthly trend
        monthly_data = analytics_service.get_monthly_trend(records.data if records.data else [])
        
        # Determine trend direction
        if len(monthly_data) >= 2:
            recent = monthly_data[-1]["percentage"]
            previous = monthly_data[-2]["percentage"]
            if recent > previous + 5:
                trend = "improving"
            elif recent < previous - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return StudentTrend(
            student_id=student_id,
            student_name=student.data.get("full_name", "Unknown"),
            monthly_data=monthly_data,
            trend=trend
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching student trend: {str(e)}"
        )


@router.get("/alerts", response_model=list[DefaulterAlert])
async def get_defaulter_alerts(threshold: float = 75.0, current_user: dict = Depends(lambda: {})):
    """Get list of students below attendance threshold"""
    if current_user.get("role") not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get all students
        students = supabase.table("profiles").select("*").eq("role", "student").execute()
        
        defaulters = []
        
        for student in students.data:
            # Get attendance records for student
            records = supabase.table("attendance_records").select("*").eq("student_id", student["id"]).execute()
            
            if not records.data:
                continue
            
            # Calculate summary
            summary = analytics_service.get_student_attendance_summary(records.data)
            
            if summary["percentage"] < threshold:
                # Get subject breakdown
                subject_records = {}
                for record in records.data:
                    subject_id = record["subject_id"]
                    if subject_id not in subject_records:
                        subject_records[subject_id] = []
                    subject_records[subject_id].append(record)
                
                subject_breakdown = []
                for subject_id, subj_records in subject_records.items():
                    subject = supabase.table("subjects").select("name").eq("id", subject_id).single().execute()
                    subj_summary = analytics_service.get_student_attendance_summary(subj_records)
                    subject_breakdown.append({
                        "subject_name": subject.data["name"] if subject.data else "Unknown",
                        "percentage": subj_summary["percentage"]
                    })
                
                # Determine trend
                monthly_data = analytics_service.get_monthly_trend(records.data)
                if len(monthly_data) >= 3:
                    recent_avg = sum(m["percentage"] for m in monthly_data[-3:]) / 3
                    if recent_avg < summary["percentage"]:
                        trend = "improving"
                    else:
                        trend = "declining"
                else:
                    trend = "insufficient_data"
                
                defaulters.append(DefaulterAlert(
                    student_id=student["id"],
                    student_name=student.get("full_name", "Unknown"),
                    roll_number=student.get("roll_number", "N/A"),
                    department=student.get("department", "N/A"),
                    semester=student.get("semester", 0),
                    overall_attendance=summary["percentage"],
                    subject_breakdown=subject_breakdown,
                    trend=trend
                ))
        
        # Sort by attendance percentage (lowest first)
        defaulters.sort(key=lambda x: x.overall_attendance)
        
        return defaulters
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching defaulter alerts: {str(e)}"
        )


@router.get("/subject/{subject_id}/hourly", response_model=HourlyAnalytics)
async def get_hourly_analytics(subject_id: str, current_user: dict = Depends(lambda: {})):
    """Get hourly attendance patterns for a subject"""
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
        
        # Get attendance records
        records = supabase.table("attendance_records").select("*").eq("subject_id", subject_id).execute()
        
        # Get session times to determine hour
        sessions = supabase.table("class_sessions").select("*").eq("subject_id", subject_id).execute()
        
        # Map attendance records to their session times
        records_with_time = []
        for record in records.data if records.data else []:
            session = next((s for s in sessions.data if s["id"] == record["session_id"]), None)
            if session and record.get("marked_at"):
                marked_at = datetime.fromisoformat(record["marked_at"].replace("Z", "+00:00"))
                record_with_time = record.copy()
                record_with_time["marked_at"] = marked_at
                records_with_time.append(record_with_time)
        
        # Analyze hourly patterns
        hourly_analysis = analytics_service.analyze_hourly_patterns(records_with_time)
        
        return HourlyAnalytics(
            subject_id=subject_id,
            subject_name=subject.data["name"],
            hourly_data=hourly_analysis["hourly_data"],
            best_hour=hourly_analysis["best_hour"],
            worst_hour=hourly_analysis["worst_hour"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching hourly analytics: {str(e)}"
        )
