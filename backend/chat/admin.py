from django.contrib import admin
from django.utils.html import format_html
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_email', 'message_count', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['session_id', 'user__email', 'user__username']
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'message_count']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'

    # Add these to your ChatSessionAdmin class
    actions = ['deactivate_sessions', 'delete_old_sessions']

    def deactivate_sessions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} sessions were successfully deactivated.')
    deactivate_sessions.short_description = "Deactivate selected sessions"

    def delete_old_sessions(self, request, queryset):
        from datetime import datetime, timedelta
        old_date = datetime.now() - timedelta(days=30)
        old_sessions = queryset.filter(updated_at__lt=old_date)
        count = old_sessions.count()
        old_sessions.delete()
        self.message_user(request, f'{count} old sessions were deleted.')
    delete_old_sessions.short_description = "Delete sessions older than 30 days"

    
    # Show messages inline when viewing a session
    class ChatMessageInline(admin.TabularInline):
        model = ChatMessage
        readonly_fields = ['message_type', 'content', 'timestamp']
        extra = 0
        can_delete = False
        
        def has_add_permission(self, request, obj=None):
            return False
    
    inlines = [ChatMessageInline]

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_link', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp', 'session__user']
    search_fields = ['content', 'session__session_id', 'session__user__email']
    readonly_fields = ['session', 'message_type', 'content', 'timestamp', 'metadata']
    
    def session_link(self, obj):
        return format_html(
            '<a href="/admin/chat/chatsession/{}/change/">{}</a>',
            obj.session.id,
            obj.session.session_id[:8] + '...'
        )
    session_link.short_description = 'Session'
    
    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Message Preview'
    
    def has_add_permission(self, request):
        return False  # Don't allow adding messages directly
