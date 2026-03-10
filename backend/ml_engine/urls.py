from django.urls import path
from .views import (
    RecommendationAPI, AdminRetrainView, TrainingStatusView, 
    ModelListView, ModelActionView, AdminModelManagerView,
    AdaptiveStartView, AdaptivePredictView, AdaptiveExplainView,
    QuestionTextView, TestModelView,
    DatasetListView, DatasetDetailView, DatasetDeleteView
)
from .views_rasa import RasaAdminView, RasaFileAPI, RasaTrainAPI

urlpatterns = [
    path('predict/', RecommendationAPI.as_view(), name='predict'),
    path('status/', TrainingStatusView.as_view(), name='status'),
    path('models/', ModelListView.as_view(), name='model_list'),
    path('models/action/', ModelActionView.as_view(), name='model_action'),
    
    # Adaptive recommendation endpoints
    path('adaptive/start/', AdaptiveStartView.as_view(), name='adaptive_start'),
    path('adaptive/predict/', AdaptivePredictView.as_view(), name='adaptive_predict'),
    path('adaptive/explain/', AdaptiveExplainView.as_view(), name='adaptive_explain'),
    
    # Question text endpoints
    path('question/<int:index>/', QuestionTextView.as_view(), name='question_text'),
    path('questions/', QuestionTextView.as_view(), name='questions_batch'),
    
    # Test interface
    path('test/', TestModelView.as_view(), name='test_model'),
    
    # Dataset management endpoints
    path('datasets/', DatasetListView.as_view(), name='dataset_list'),
    path('datasets/<str:filename>/', DatasetDetailView.as_view(), name='dataset_detail'),
    path('datasets/<str:filename>/delete/', DatasetDeleteView.as_view(), name='dataset_delete'),

    # Rasa Admin endpoints
    path('rasa/file/<str:file_type>/', RasaFileAPI.as_view(), name='rasa_file_api'),
    path('rasa/train/', RasaTrainAPI.as_view(), name='rasa_train_api'),
]
