from django.contrib import admin
from django.urls import path, include

# Customize admin site
admin.site.site_header = "Chat Application Admin"
admin.site.site_title = "Chat Admin Portal"
admin.site.index_title = "Welcome to Chat Administration"

from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/ml/', permanent=True)),
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/ml/', include('ml_engine.urls')),
    path('ml/', include('ml_engine.urls_pages')),
]
