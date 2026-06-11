import qrcode
import uuid
from io import BytesIO
from datetime import datetime, timedelta
from typing import Tuple, Optional


class QRService:
    @staticmethod
    def generate_token() -> str:
        """Generate a unique QR token using UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def generate_qr_code(token: str) -> bytes:
        """Generate QR code image as bytes"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def validate_token(
        provided_token: str,
        stored_token: str,
        expires_at: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Validate QR token
        Returns (is_valid, error_message)
        """
        if not provided_token or not stored_token:
            return False, "Token is missing"
        
        if provided_token != stored_token:
            return False, "Invalid token"
        
        if expires_at and datetime.utcnow() > expires_at:
            return False, "Token has expired"
        
        return True, "Token is valid"

    @staticmethod
    def get_expiration_time(minutes: int = 5) -> datetime:
        """Get expiration time for QR token (default 5 minutes)"""
        return datetime.utcnow() + timedelta(minutes=minutes)
