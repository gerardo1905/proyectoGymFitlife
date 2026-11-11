from django.contrib import admin
from .models import Socio, RegistroAcceso

@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombres', 'apellidos', 'telefono', 'email', 'activo', 'fecha_registro')
    list_filter = ('activo', 'fecha_registro')
    search_fields = ('rut', 'nombres', 'apellidos', 'telefono', 'email')

@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    list_display = ('socio', 'fecha_hora_ingreso', 'fecha_hora_salida', 'permitido', 'motivo_rechazo', 'registrado_por')
    list_filter = ('permitido', 'fecha_hora_ingreso')
    search_fields = ('socio__rut', 'socio__nombres', 'socio__apellidos')