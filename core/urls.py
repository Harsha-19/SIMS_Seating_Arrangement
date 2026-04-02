from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.admin_site_map if hasattr(admin.site, 'admin_site_map') else admin.site.urls),
    path('api/', include('api.urls')),
    path('', include('dashboard.urls')),
]
