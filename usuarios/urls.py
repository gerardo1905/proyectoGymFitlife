from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/cambiar-password/', views.cambiar_password_view, name='cambiar_password'),
    path('trabajadores/', views.usuario_lista_view, name='usuario_lista'),
    path('trabajadores/crear/', views.usuario_crear_view, name='usuario_crear'),
    path('trabajadores/<int:pk>/editar/', views.usuario_editar_view, name='usuario_editar'),
    path('<int:pk>/cambiar-password/', views.usuario_cambiar_password_view, name='usuario_cambiar_password'),
]