from django.contrib import admin
from .models import CategoriaGasto, Gasto

@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'categoria', 'importe', 'fecha', 'usuario_responsable')
    list_filter = ('categoria', 'fecha')
    search_fields = ('concepto', 'comprobante')
