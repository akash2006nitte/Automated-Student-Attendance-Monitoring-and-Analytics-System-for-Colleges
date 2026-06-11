from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from supabase import Client
import os
from datetime import datetime, date
from dotenv import load_dotenv

from services.report_service import ReportService
from services.analytics_service import AnalyticsService

load_dotenv()

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()
report_service = ReportService()
analytics_service = AnalyticsService()


@router.get("/student/{student_id}/pdf")
async def generate_student_pdf_report(student_id: str, current_user: dict = Depends(lambda: {})):
    """Generate PDF attendance report for a student"""
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
        records = supabase.table("attendance_records").select("*").eq("student_id", student_id).order(
            "marked_at", desc=True
        ).execute()
        
        # Enrich records with subject names
        enriched_records = []
        for record in records.data if records.data else []:
            subject = supabase.table("subjects").select("name").eq("id", record["subject_id"]).single().execute()
            record_with_subject = record.copy()
            record_with_subject["subject_name"] = subject.data["name"] if subject.data else "Unknown"
            enriched_records.append(record_with_subject)
        
        # Calculate summary
        summary = analytics_service.get_student_attendance_summary(enriched_records)
        
        # Generate PDF
        pdf_bytes = report_service.generate_pdf_report(
            student_data=student.data,
            attendance_records=enriched_records,
            summary=summary
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=attendance_report_{student.data.get('roll_number', student_id)}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF report: {str(e)}"
        )


@router.get("/subject/{subject_id}/excel")
async def generate_subject_excel_report(subject_id: str, current_user: dict = Depends(lambda: {})):
    """Generate Excel attendance report for a subject"""
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
        
        # Get attendance records with student info
        records = supabase.table("attendance_records").select("*").eq("subject_id", subject_id).order(
            "marked_at", desc=True
        ).execute()
        
        # Enrich records with student info
        enriched_records = []
        for record in records.data if records.data else []:
            student = supabase.table("profiles").select("full_name", "roll_number").eq(
                "id", record["student_id"]
            ).single().execute()
            record_with_student = record.copy()
            record_with_student["student_name"] = student.data.get("full_name") if student.data else "Unknown"
            record_with_student["roll_number"] = student.data.get("roll_number") if student.data else "N/A"
            enriched_records.append(record_with_student)
        
        # Generate Excel
        excel_bytes = report_service.generate_excel_report(
            subject_name=subject.data["name"],
            attendance_data=enriched_records
        )
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=attendance_{subject.data['code']}.xlsx"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating Excel report: {str(e)}"
        )


@router.get("/department/{department}/monthly")
async def get_monthly_department_report(department: str, year: int, month: int, current_user: dict = Depends(lambda: {})):
    """Get monthly attendance summary for a department"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get date range for the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Get all subjects in department
        subjects = supabase.table("subjects").select("*").eq("department", department).execute()
        
        subject_ids = [s["id"] for s in subjects.data] if subjects.data else []
        
        if not subject_ids:
            return {
                "department": department,
                "year": year,
                "month": month,
                "total_subjects": 0,
                "total_sessions": 0,
                "average_attendance": 0.0,
                "subject_breakdown": []
            }
        
        # Get sessions in the date range
        sessions = supabase.table("class_sessions").select("*").in_(
            "subject_id", subject_ids
        ).gte("date", start_date.isoformat()).lt("date", end_date.isoformat()).execute()
        
        session_ids = [s["id"] for s in sessions.data] if sessions.data else []
        
        # Get attendance records for these sessions
        if session_ids:
            records = supabase.table("attendance_records").select("*").in_(
                "session_id", session_ids
            ).execute()
        else:
            records = None
        
        # Calculate statistics
        total_sessions = len(sessions.data) if sessions.data else 0
        total_records = len(records.data) if records and records.data else 0
        present = sum(1 for r in records.data if r["status"] in ["present", "late"]) if records and records.data else 0
        average_attendance = analytics_service.calculate_attendance_percentage(total_records, present)
        
        # Subject breakdown
        subject_breakdown = []
        for subject in subjects.data:
            subject_sessions = [s for s in sessions.data if s["subject_id"] == subject["id"]] if sessions.data else []
            subject_session_ids = [s["id"] for s in subject_sessions]
            
            if subject_session_ids:
                subject_records = [r for r in records.data if r["session_id"] in subject_session_ids] if records.data else []
                subj_present = sum(1 for r in subject_records if r["status"] in ["present", "late"])
                subj_total = len(subject_records)
                subj_percentage = analytics_service.calculate_attendance_percentage(subj_total, subj_present)
            else:
                subj_present = 0
                subj_total = 0
                subj_percentage = 0.0
            
            subject_breakdown.append({
                "subject_name": subject["name"],
                "subject_code": subject["code"],
                "total_sessions": len(subject_sessions),
                "attendance_percentage": subj_percentage
            })
        
        return {
            "department": department,
            "year": year,
            "month": month,
            "total_subjects": len(subjects.data) if subjects.data else 0,
            "total_sessions": total_sessions,
            "average_attendance": average_attendance,
            "subject_breakdown": subject_breakdown
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating monthly report: {str(e)}"
        )
