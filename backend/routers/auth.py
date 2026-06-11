from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
import os
from dotenv import load_dotenv

from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

load_dotenv()

# Initialize Supabase client for auth
supabase: Client = Client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user with email and password"""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_id = auth_response.user.id
        access_token = auth_response.session.access_token
        
        # Fetch user profile
        profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        profile = profile_response.data
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=profile["id"],
                email=auth_response.user.email,
                full_name=profile.get("full_name"),
                role=profile.get("role"),
                department=profile.get("department"),
                semester=profile.get("semester"),
                roll_number=profile.get("roll_number"),
                photo_url=profile.get("photo_url")
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name,
                    "role": request.role
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        user_id = auth_response.user.id
        access_token = auth_response.session.access_token if auth_response.session else None
        
        # Create profile (trigger will handle this, but we'll ensure it)
        profile_data = {
            "id": user_id,
            "full_name": request.full_name,
            "role": request.role,
            "department": request.department,
            "semester": request.semester,
            "roll_number": request.roll_number
        }
        
        supabase.table("profiles").insert(profile_data).execute()
        
        # Fetch the created profile
        profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data
        
        return TokenResponse(
            access_token=access_token or "",
            token_type="bearer",
            user=UserResponse(
                id=profile["id"],
                email=auth_response.user.email,
                full_name=profile.get("full_name"),
                role=profile.get("role"),
                department=profile.get("department"),
                semester=profile.get("semester"),
                roll_number=profile.get("roll_number"),
                photo_url=profile.get("photo_url")
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: str):
    """Get current user profile"""
    try:
        profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = profile_response.data
        
        # Get email from auth.users
        auth_user = supabase.auth.get_user(user_id)
        email = auth_user.user.email if auth_user.user else ""
        
        return UserResponse(
            id=profile["id"],
            email=email,
            full_name=profile.get("full_name"),
            role=profile.get("role"),
            department=profile.get("department"),
            semester=profile.get("semester"),
            roll_number=profile.get("roll_number"),
            photo_url=profile.get("photo_url")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )
