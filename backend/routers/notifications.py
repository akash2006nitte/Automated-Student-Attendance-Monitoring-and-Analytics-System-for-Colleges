from fastapi import APIRouter, HTTPException, status
from supabase import Client
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from schemas.notification import NotificationCreate, NotificationResponse
from services.notification_service import NotificationService
from services.analytics_service import AnalyticsService

load_dotenv()

supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()
notification_service = NotificationService(supabase)
analytics_service = AnalyticsService()

# Scheduler for background tasks
scheduler = AsyncIOScheduler()


async def check_defaulters():
    """Background task to check for defaulters and send notifications"""
    try:
        # Get all students
        students = supabase.table("profiles").select("*").eq("role", "student").execute()
        
        threshold = 75.0
        
        for student in students.data:
            # Get attendance records
            records = supabase.table("attendance_records").select("*").eq("student_id", student["id"]).execute()
            
            if not records.data:
                continue
            
            # Calculate attendance
            summary = analytics_service.get_student_attendance_summary(records.data)
            
            if summary["percentage"] < threshold:
                # Send notification
                notification_service.create_notification(
                    user_id=student["id"],
                    title="Low Attendance Warning",
                    message=f"Your attendance is {summary['percentage']}%. Please improve your attendance to avoid academic consequences.",
                    notification_type="warning"
                )
                
                # Also notify parent (if parent email exists in profile)
                # This would require extending the profile schema
                
    except Exception as e:
        print(f"Error in defaulter check: {str(e)}")


@router.on_event("startup")
async def startup_event():
    """Start the scheduler on startup"""
    scheduler.add_job(
        check_defaulters,
        CronTrigger(day_of_week="sun", hour=9, minute=0),
        id="check_defaulters",
        replace_existing=True
    )
    scheduler.start()


@router.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler"""
    scheduler.shutdown()


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(unread_only: bool = False, current_user: dict = Depends(lambda: {})):
    """Get all notifications for current user"""
    try:
        notifications = notification_service.get_user_notifications(
            user_id=current_user["id"],
            unread_only=unread_only
        )
        
        return [
            NotificationResponse(
                id=n["id"],
                user_id=n["user_id"],
                title=n["title"],
                message=n["message"],
                type=n.get("type"),
                is_read=n["is_read"],
                created_at=n["created_at"]
            )
            for n in notifications
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching notifications: {str(e)}"
        )


@router.post("/send")
async def send_notification(notification: NotificationCreate, current_user: dict = Depends(lambda: {})):
    """Send a notification to a user (admin/teacher only)"""
    if current_user.get("role") not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        result = notification_service.create_notification(
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.type
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send notification"
            )
        
        return {"message": "Notification sent successfully", "notification_id": result["id"]}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending notification: {str(e)}"
        )


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(lambda: {})):
    """Mark a notification as read"""
    try:
        # Verify notification belongs to user
        notification = supabase.table("notifications").select("*").eq("id", notification_id).single().execute()
        
        if not notification.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        if notification.data["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = notification_service.mark_as_read(notification_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark notification as read"
            )
        
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking notification: {str(e)}"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_read(current_user: dict = Depends(lambda: {})):
    """Mark all notifications as read for current user"""
    try:
        success = notification_service.mark_all_as_read(current_user["id"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark notifications as read"
            )
        
        return {"message": "All notifications marked as read"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking notifications: {str(e)}"
        )


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(lambda: {})):
    """Get count of unread notifications"""
    try:
        count = notification_service.get_unread_count(current_user["id"])
        return {"unread_count": count}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching unread count: {str(e)}"
        )
