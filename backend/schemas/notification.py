from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    message: str
    type: Optional[str] = None


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: Optional[str] = None
    is_read: bool
    created_at: str
