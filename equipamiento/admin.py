from django.contrib import admin
from .models import Equipo, Mantenimiento

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('codigo_unico', 'nombre', 'ubicacion', 'estado', 'fecha_adquisicion')
    list_filter = ('estado',)
    search_fields = ('codigo_unico', 'nombre', 'ubicacion')


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'usuario_responsable', 'fecha_programada', 'fecha_realizada', 'costo')
    list_filter = ('fecha_programada',)
    search_fields = ('equipo__nombre', 'equipo__codigo_unico')
