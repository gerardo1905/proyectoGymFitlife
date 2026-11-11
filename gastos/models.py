from django.db import models
from django.conf import settings

class CategoriaGasto(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return self.nombre


class Gasto(models.Model):
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.RESTRICT, related_name='gastos', verbose_name="Categoría")
    usuario_responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Registrado Por")
    concepto = models.CharField(max_length=150, verbose_name="Concepto / Detalle")
    importe = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Importe $")
    fecha = models.DateField(verbose_name="Fecha del Gasto")
    comprobante = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ref. Comprobante")

    def __str__(self):
        return f"Gasto: {self.concepto} - ${self.importe}"