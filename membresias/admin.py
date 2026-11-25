from django.contrib import admin
from .models import Plan, Membresia, Pago


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'duracion_dias', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ('socio', 'plan', 'fecha_inicio', 'fecha_fin', 'estado', 'importe_acordado', 'registrado_por')
    list_filter = ('estado', 'plan')
    search_fields = ('socio__rut', 'socio__nombres', 'socio__apellidos')
    # Las fechas y el importe los calcula el sistema; ni siquiera desde el
    # admin se editan a mano (evita "regalar" días o cambiar precios).
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'importe_acordado', 'registrado_por', 'qr_token', 'fecha_congelamiento')


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'membresia', 'monto', 'metodo_pago', 'fecha_pago', 'usuario_responsable')
    list_filter = ('metodo_pago', 'fecha_pago')
    search_fields = ('membresia__socio__rut', 'comprobante_ref')

    # Los pagos son registros contables: solo lectura en el admin.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
