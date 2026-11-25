from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

# El backend SOLO expone la API REST (y el admin de Django para soporte).
# La interfaz de usuario vive en el proyecto separado fitlife_frontend (React).
urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    # En local los archivos (QR) se sirven desde MEDIA_ROOT; en AWS van a S3.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
