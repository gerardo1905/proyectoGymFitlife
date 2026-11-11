from django.db import models
from django.conf import settings

class Equipo(models.Model):
    ESTADOS = (
        ('DISPONIBLE', 'Disponible'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('FUERA_SERVICIO', 'Fuera de Servicio'),
        ('BAJA', 'Dado de Baja'),
    )

    codigo_unico = models.CharField(max_length=50, unique=True, verbose_name="Código de Equipo")
    nombre = models.CharField(max_length=100, verbose_name="Nombre Máquina/Accesorio")
    ubicacion = models.CharField(max_length=100, verbose_name="Ubicación en Gimnasio")
    fecha_adquisicion = models.DateField(verbose_name="Fecha Adquisición")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE', verbose_name="Estado")

    def __str__(self):
        return f"{self.nombre} [{self.codigo_unico}] - {self.estado}"


class Mantenimiento(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='mantenimientos', verbose_name="Equipo")
    usuario_responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Responsable")
    fecha_programada = models.DateField(verbose_name="Fecha Programada")
    fecha_realizada = models.DateField(blank=True, null=True, verbose_name="Fecha Ejecución")
    trabajo_realizado = models.TextField(blank=True, null=True, verbose_name="Trabajo Realizado")
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo $")

    def __str__(self):
        return f"Mantenimiento {self.equipo.nombre} ({self.fecha_programada})"