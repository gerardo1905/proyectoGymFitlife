from django.urls import path
from . import views

urlpatterns = [
    path('', views.equipo_lista_view, name='equipo_lista'),
    path('crear/', views.equipo_crear_view, name='equipo_crear'),
    path('<int:pk>/', views.equipo_detalle_view, name='equipo_detalle'),
    path('<int:pk>/editar/', views.equipo_editar_view, name='equipo_editar'),
]
