from .auth import router as auth_router
from .attendance import router as attendance_router
from .analytics import router as analytics_router
from .notifications import router as notifications_router
from .leave import router as leave_router
from .reports import router as reports_router

__all__ = [
    "auth_router",
    "attendance_router",
    "analytics_router",
    "notifications_router",
    "leave_router",
    "reports_router",
]
