from django.contrib import admin
from .models import Ejercicio, Rutina, DetalleRutina

@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'grupo_muscular', 'activo')
    list_filter = ('grupo_muscular', 'activo')
    search_fields = ('nombre', 'grupo_muscular')


class DetalleRutinaInline(admin.TabularInline):
    model = DetalleRutina
    extra = 1


@admin.register(Rutina)
class RutinaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'socio', 'entrenador', 'objetivo', 'fecha_inicio', 'fecha_fin', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre', 'socio__rut', 'socio__nombres', 'socio__apellidos')
    inlines = [DetalleRutinaInline]
