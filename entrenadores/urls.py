from django.urls import path
from . import views

urlpatterns = [
    path('', views.entrenador_lista_view, name='entrenador_lista'),
    path('mis-socios/', views.mis_socios_view, name='mis_socios'),
    path('<int:pk>/', views.entrenador_detalle_view, name='entrenador_detalle'),
    path('<int:pk>/editar/', views.entrenador_editar_view, name='entrenador_editar'),
    path('asignacion/<int:pk>/finalizar/', views.asignacion_finalizar_view, name='asignacion_finalizar'),
]
