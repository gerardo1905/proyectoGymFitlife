from django.contrib import admin
from .models import TipoClase, Sala, Entrenador, SesionClase, InscripcionClase

@admin.register(TipoClase)
class TipoClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'duracion_minutos', 'activa')

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'capacidad_maxima', 'activa')

@admin.register(SesionClase)
class SesionClaseAdmin(admin.ModelAdmin):
    list_display = ('tipo_clase', 'sala', 'entrenador', 'fecha', 'hora_inicio', 'cupo_maximo', 'estado')
    list_filter = ('estado', 'fecha', 'tipo_clase')

@admin.register(InscripcionClase)
class InscripcionClaseAdmin(admin.ModelAdmin):
    list_display = ('socio', 'sesion', 'fecha_inscripcion', 'asistio')
    list_filter = ('asistio',)