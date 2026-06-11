from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class NotificationBase(BaseModel):
    user_id: UUID
    title: str
    message: str
    type: Optional[str] = None
    is_read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class Notification(NotificationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
