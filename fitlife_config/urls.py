from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('socios/', include('socios.urls')),
    path('membresias/', include('membresias.urls')),
    path('clases/', include('clases.urls')),
    path('entrenadores/', include('entrenadores.urls')),
    path('equipamiento/', include('equipamiento.urls')),
    path('gastos/', include('gastos.urls')),
]
handler404 = 'dashboard.views.error_404_view'