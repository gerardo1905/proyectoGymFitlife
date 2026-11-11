from django.db import models
from socios.models import Socio
from entrenadores.models import Entrenador

class Ejercicio(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Ejercicio")
    grupo_muscular = models.CharField(max_length=50, verbose_name="Grupo Muscular")
    instrucciones = models.TextField(blank=True, null=True, verbose_name="Instrucciones")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return f"{self.nombre} ({self.grupo_muscular})"


class Rutina(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='rutinas', verbose_name="Socio")
    entrenador = models.ForeignKey(Entrenador, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Entrenador Creador")
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Rutina")
    objetivo = models.CharField(max_length=150, verbose_name="Objetivo Principal")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(blank=True, null=True, verbose_name="Fecha de Término")
    activa = models.BooleanField(default=True, verbose_name="Rutina Vigente")

    def __str__(self):
        return f"Rutina: {self.nombre} - Socio: {self.socio.nombres}"


class DetalleRutina(models.Model):
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name='detalles', verbose_name="Rutina")
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.RESTRICT, verbose_name="Ejercicio")
    dia_semana = models.CharField(max_length=20, verbose_name="Día de la Semana")
    orden = models.IntegerField(default=1, verbose_name="Orden Ejercicio")
    series = models.IntegerField(verbose_name="Series")
    repeticiones = models.IntegerField(verbose_name="Repeticiones")
    carga_kg = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Carga (Kg)")
    descanso_seg = models.IntegerField(default=60, verbose_name="Descanso (Segundos)")

    def __str__(self):
        return f"{self.rutina.nombre} - {self.ejercicio.nombre} ({self.series}x{self.repeticiones})"