from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from jose import jwt, JWTError
import uvicorn

from routers import auth, attendance, analytics, notifications, leave, reports
from services.notification_service import NotificationService

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Initialize notification service
notification_service = NotificationService(supabase)

# Security
security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Attendance System Backend...")
    yield
    # Shutdown
    print("Shutting down Attendance System Backend...")


# Create FastAPI app
app = FastAPI(
    title="Attendance System API",
    description="Automated Student Attendance Monitoring and Analytics System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# JWT Verification
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Supabase"""
    token = credentials.credentials
    try:
        # Verify using Supabase JWT secret
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_user(payload: dict = Depends(verify_token)):
    """Get current user from JWT payload"""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier"
        )
    
    # Fetch user profile from Supabase
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )


async def require_role(required_role: str):
    """Dependency to require specific role"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != required_role and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. {required_role} role required"
            )
        return current_user
    return role_checker


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"], dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"], dependencies=[Depends(get_current_user)])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"], dependencies=[Depends(get_current_user)])
app.include_router(leave.router, prefix="/api/leave", tags=["Leave"], dependencies=[Depends(get_current_user)])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "attendance-system-backend"}


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Attendance System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
