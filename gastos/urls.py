from django.urls import path
from . import views

urlpatterns = [
    path('', views.gasto_lista_view, name='gasto_lista'),
    path('crear/', views.gasto_crear_view, name='gasto_crear'),
    path('categorias/', views.categoria_lista_view, name='categoria_lista'),
    path('categorias/crear/', views.categoria_crear_view, name='categoria_crear'),
    path('categorias/<int:pk>/editar/', views.categoria_editar_view, name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/', views.categoria_eliminar_view, name='categoria_eliminar'),
]
