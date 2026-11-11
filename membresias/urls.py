from django.urls import path
from . import views

urlpatterns = [
    # Rutas de Planes
    path('planes/', views.plan_lista_view, name='plan_lista'),
    path('planes/crear/', views.plan_crear_view, name='plan_crear'),
    path('planes/<int:pk>/editar/', views.plan_editar_view, name='plan_editar'),

    # Rutas de Membresías
    path('', views.membresia_lista_view, name='membresia_lista'),
    path('crear/', views.membresia_crear_view, name='membresia_crear'),
    path('crear/socio/<int:socio_id>/', views.membresia_crear_view, name='membresia_crear_socio'),
    path('<int:pk>/estado/<str:nuevo_estado>/', views.membresia_cambiar_estado_view, name='membresia_cambiar_estado'),

    # Rutas de Pagos
    path('<int:membresia_id>/pago/', views.pago_registrar_view, name='pago_registrar'),
]