from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', views.refresh_token_view, name='token_refresh'),
    path('csrf-token/', views.csrf_token_view, name='csrf_token'),
    path('profile/', views.ProfileView.as_view(), name='user_profile'),
    path('change-password/', views.change_password_view, name='change_password'),
]
