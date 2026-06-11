from fastapi import APIRouter, HTTPException, status
from supabase import Client
import os
from datetime import datetime
from dotenv import load_dotenv

from schemas.leave import LeaveRequestCreate, LeaveRequestResponse, LeaveReview

load_dotenv()

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()


@router.post("/", response_model=LeaveRequestResponse)
async def create_leave_request(request: LeaveRequestCreate, current_user: dict = Depends(lambda: {})):
    """Student submits a leave request"""
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit leave requests"
        )
    
    try:
        # Get subject
        subject = supabase.table("subjects").select("*").eq("id", request.subject_id).single().execute()
        if not subject.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found"
            )
        
        # Create leave request
        leave_data = {
            "student_id": current_user["id"],
            "subject_id": request.subject_id,
            "from_date": request.from_date.isoformat(),
            "to_date": request.to_date.isoformat(),
            "reason": request.reason,
            "document_url": request.document_url,
            "status": "pending"
        }
        
        result = supabase.table("leave_requests").insert(leave_data).execute()
        leave_request = result.data[0] if result.data else None
        
        if not leave_request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create leave request"
            )
        
        # Get student info
        student = supabase.table("profiles").select("full_name").eq("id", current_user["id"]).single().execute()
        
        return LeaveRequestResponse(
            id=leave_request["id"],
            student_id=leave_request["student_id"],
            student_name=student.data.get("full_name") if student.data else None,
            subject_id=leave_request["subject_id"],
            subject_name=subject.data["name"],
            from_date=leave_request["from_date"],
            to_date=leave_request["to_date"],
            reason=leave_request["reason"],
            document_url=leave_request["document_url"],
            status=leave_request["status"],
            reviewed_by=leave_request["reviewed_by"],
            reviewed_by_name=None,
            reviewed_at=leave_request["reviewed_at"],
            created_at=leave_request["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating leave request: {str(e)}"
        )


@router.get("/student/{student_id}", response_model=list[LeaveRequestResponse])
async def get_student_leave_history(student_id: str, current_user: dict = Depends(lambda: {})):
    """Get leave history for a student"""
    if current_user["id"] != student_id and current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        requests = supabase.table("leave_requests").select("*").eq("student_id", student_id).order(
            "created_at", desc=True
        ).execute()
        
        result = []
        for req in requests.data if requests.data else []:
            # Get student name
            student = supabase.table("profiles").select("full_name").eq("id", req["student_id"]).single().execute()
            
            # Get subject name
            subject = supabase.table("subjects").select("name").eq("id", req["subject_id"]).single().execute()
            
            # Get reviewer name
            reviewer_name = None
            if req["reviewed_by"]:
                reviewer = supabase.table("profiles").select("full_name").eq("id", req["reviewed_by"]).single().execute()
                reviewer_name = reviewer.data.get("full_name") if reviewer.data else None
            
            result.append(LeaveRequestResponse(
                id=req["id"],
                student_id=req["student_id"],
                student_name=student.data.get("full_name") if student.data else None,
                subject_id=req["subject_id"],
                subject_name=subject.data["name"] if subject.data else None,
                from_date=req["from_date"],
                to_date=req["to_date"],
                reason=req["reason"],
                document_url=req["document_url"],
                status=req["status"],
                reviewed_by=req["reviewed_by"],
                reviewed_by_name=reviewer_name,
                reviewed_at=req["reviewed_at"],
                created_at=req["created_at"]
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching leave history: {str(e)}"
        )


@router.get("/pending", response_model=list[LeaveRequestResponse])
async def get_pending_leave_requests(current_user: dict = Depends(lambda: {})):
    """Get all pending leave requests for teacher's subjects"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get subjects taught by teacher
        if current_user.get("role") == "teacher":
            subjects = supabase.table("subjects").select("id").eq("teacher_id", current_user["id"]).execute()
            subject_ids = [s["id"] for s in subjects.data] if subjects.data else []
        else:
            # Admin sees all
            subjects = supabase.table("subjects").select("id").execute()
            subject_ids = [s["id"] for s in subjects.data] if subjects.data else []
        
        if not subject_ids:
            return []
        
        # Get pending requests for these subjects
        requests = supabase.table("leave_requests").select("*").in_(
            "subject_id", subject_ids
        ).eq("status", "pending").order("created_at", desc=True).execute()
        
        result = []
        for req in requests.data if requests.data else []:
            # Get student name
            student = supabase.table("profiles").select("full_name", "roll_number").eq("id", req["student_id"]).single().execute()
            
            # Get subject name
            subject = supabase.table("subjects").select("name").eq("id", req["subject_id"]).single().execute()
            
            result.append(LeaveRequestResponse(
                id=req["id"],
                student_id=req["student_id"],
                student_name=student.data.get("full_name") if student.data else None,
                subject_id=req["subject_id"],
                subject_name=subject.data["name"] if subject.data else None,
                from_date=req["from_date"],
                to_date=req["to_date"],
                reason=req["reason"],
                document_url=req["document_url"],
                status=req["status"],
                reviewed_by=req["reviewed_by"],
                reviewed_by_name=None,
                reviewed_at=req["reviewed_at"],
                created_at=req["created_at"]
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching pending requests: {str(e)}"
        )


@router.patch("/{request_id}/review")
async def review_leave_request(request_id: str, review: LeaveReview, current_user: dict = Depends(lambda: {})):
    """Teacher approves or rejects a leave request"""
    if current_user.get("role") not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get leave request
        leave_request = supabase.table("leave_requests").select("*").eq("id", request_id).single().execute()
        if not leave_request.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found"
            )
        
        if leave_request.data["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave request has already been reviewed"
            )
        
        # Update leave request
        update_data = {
            "status": review.status,
            "reviewed_by": current_user["id"],
            "reviewed_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("leave_requests").update(update_data).eq("id", request_id).execute()
        
        # Send notification to student
        student_id = leave_request.data["student_id"]
        subject = supabase.table("subjects").select("name").eq("id", leave_request.data["subject_id"]).single().execute()
        subject_name = subject.data["name"] if subject.data else "Subject"
        
        if review.status == "approved":
            message = f"Your leave request for {subject_name} has been approved."
        else:
            message = f"Your leave request for {subject_name} has been rejected."
        
        supabase.table("notifications").insert({
            "user_id": student_id,
            "title": f"Leave Request {review.status.capitalize()}",
            "message": message,
            "type": "leave"
        }).execute()
        
        return {"message": f"Leave request {review.status} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reviewing leave request: {str(e)}"
        )
