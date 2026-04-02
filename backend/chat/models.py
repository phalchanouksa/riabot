from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.session_id} - {self.user.email}"

class ChatMessage(models.Model):
    MESSAGE_TYPES = (
        ('user', 'User Message'),
        ('bot', 'Bot Response'),
    )

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."


class SurveyResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='survey_results')
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='survey_results',
    )
    recommended_major = models.CharField(max_length=100)
    confidence = models.FloatField(default=0.0)
    questions_answered = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recommended_major} ({self.confidence:.2f}) - {self.user.email}"
