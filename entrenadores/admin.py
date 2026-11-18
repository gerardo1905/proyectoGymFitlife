from django.contrib import admin
from .models import AsignacionEntrenador

@admin.register(AsignacionEntrenador)
class AsignacionEntrenadorAdmin(admin.ModelAdmin):
    list_display = ('socio', 'entrenador', 'fecha_inicio', 'fecha_fin', 'activa')
    list_filter = ('activa',)
    search_fields = ('socio__rut', 'socio__nombres', 'socio__apellidos', 'entrenador__username')
