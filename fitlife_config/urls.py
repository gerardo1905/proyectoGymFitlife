from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('socios/', include('socios.urls')),
    path('membresias/', include('membresias.urls')),
    path('clases/', include('clases.urls')),
]
handler404 = 'dashboard.views.error_404_view'