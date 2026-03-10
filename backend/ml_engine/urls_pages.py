from django.urls import path
from .views import MLIndexView, AdminRetrainView, AdminModelManagerView
from .views_rasa import RasaAdminView

urlpatterns = [
    path('', MLIndexView.as_view(), name='ml_index'),
    path('tabnet/', AdminRetrainView.as_view(), name='ml_tabnet'),
    path('rasa/', RasaAdminView.as_view(), name='ml_rasa'),
    path('manager/', AdminModelManagerView.as_view(), name='ml_manager'),
]
