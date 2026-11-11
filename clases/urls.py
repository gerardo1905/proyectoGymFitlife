from django.urls import path
from . import views

urlpatterns = [
    # Actividades y Salas
    path('actividades/', views.tipo_clase_lista_view, name='tipo_clase_lista'),
    path('actividades/crear/', views.tipo_clase_crear_view, name='tipo_clase_crear'),
    path('salas/crear/', views.sala_crear_view, name='sala_crear'),

    # Sesiones y Reservas
    path('', views.sesion_lista_view, name='sesion_lista'),
    path('programar/', views.sesion_crear_view, name='sesion_crear'),
    path('<int:pk>/', views.sesion_detalle_view, name='sesion_detalle'),
    path('inscripcion/<int:pk>/cancelar/', views.inscripcion_cancelar_view, name='inscripcion_cancelar'),
    path('inscripcion/<int:pk>/asistencia/', views.asistencia_marcar_view, name='asistencia_marcar'),
]