from django.urls import path
from . import views

urlpatterns = [
    path('', views.socio_lista_view, name='socio_lista'),
    path('crear/', views.socio_crear_view, name='socio_crear'),
    path('<int:pk>/', views.socio_detalle_view, name='socio_detalle'),
    path('<int:pk>/editar/', views.socio_editar_view, name='socio_editar'),
    path('acceso/', views.acceso_control_view, name='acceso_control'),
    path('acceso/<int:pk>/salida/', views.marcar_salida_view, name='marcar_salida'),
]