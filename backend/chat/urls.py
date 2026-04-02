from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('send/', views.send_message, name='send-message'),
    path('sessions/', views.get_chat_sessions, name='chat-sessions'),
    path('history/<str:session_id>/', views.get_chat_history, name='chat-history'),
    path('survey-results/internal/', views.store_survey_result_internal, name='survey-result-internal'),
    path('session/<str:session_id>/delete/', views.delete_session, name='delete-session'),
    path('sessions/<str:session_id>/delete/', views.delete_session, name='delete-session-alt'),
]
