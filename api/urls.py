from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView

from . import views

router = DefaultRouter()
router.register('usuarios', views.UsuarioViewSet, basename='usuario')
router.register('socios', views.SocioViewSet, basename='socio')
router.register('accesos', views.AccesoViewSet, basename='acceso')
router.register('planes', views.PlanViewSet, basename='plan')
router.register('membresias', views.MembresiaViewSet, basename='membresia')
router.register('pagos', views.PagoViewSet, basename='pago')
router.register('tipos-clase', views.TipoClaseViewSet, basename='tipo-clase')
router.register('salas', views.SalaViewSet, basename='sala')
router.register('sesiones', views.SesionClaseViewSet, basename='sesion')
router.register('inscripciones', views.InscripcionViewSet, basename='inscripcion')
router.register('entrenadores', views.EntrenadorViewSet, basename='entrenador')
router.register('asignaciones', views.AsignacionViewSet, basename='asignacion')
router.register('equipos', views.EquipoViewSet, basename='equipo')
router.register('mantenimientos', views.MantenimientoViewSet, basename='mantenimiento')
router.register('categorias-gasto', views.CategoriaGastoViewSet, basename='categoria-gasto')
router.register('gastos', views.GastoViewSet, basename='gasto')

urlpatterns = [
    # Autenticación JWT
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='api_logout'),
    path('auth/perfil/', views.PerfilView.as_view(), name='api_perfil'),
    path('auth/cambiar-password/', views.CambiarPasswordView.as_view(), name='api_cambiar_password'),

    path('health/', views.health, name='api_health'),
    path('dashboard/', views.DashboardView.as_view(), name='api_dashboard'),

    # Documentación OpenAPI (Swagger)
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),

    path('', include(router.urls)),
]
