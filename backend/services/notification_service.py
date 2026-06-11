from typing import List, Optional
from supabase import Client


class NotificationService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: Optional[str] = None
    ) -> dict:
        """Create a new notification for a user"""
        notification_data = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type
        }
        
        result = self.supabase.table('notifications').insert(notification_data).execute()
        return result.data[0] if result.data else None

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[dict]:
        """Get notifications for a user"""
        query = self.supabase.table('notifications').select('*').eq('user_id', user_id)
        
        if unread_only:
            query = query.eq('is_read', False)
        
        query = query.order('created_at', desc=True)
        result = query.execute()
        return result.data if result.data else []

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        result = self.supabase.table('notifications').update(
            {'is_read': True}
        ).eq('id', notification_id).execute()
        return len(result.data) > 0 if result.data else False

    def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user"""
        result = self.supabase.table('notifications').update(
            {'is_read': True}
        ).eq('user_id', user_id).execute()
        return len(result.data) > 0 if result.data else False

    def send_bulk_notification(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        notification_type: Optional[str] = None
    ) -> List[dict]:
        """Send notification to multiple users"""
        notifications = []
        for user_id in user_ids:
            notification = self.create_notification(user_id, title, message, notification_type)
            if notification:
                notifications.append(notification)
        return notifications

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user"""
        result = self.supabase.table('notifications').select('id', count='exact').eq(
            'user_id', user_id
        ).eq('is_read', False).execute()
        return result.count if result.count else 0
