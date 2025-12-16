from django.contrib import admin
from django.urls import path, include
from apps.presentation.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.presentation.urls')),
    path('health/', health_check, name='health'),
]

