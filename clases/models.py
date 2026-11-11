from django.db import models
from django.conf import settings
from socios.models import Socio

class TipoClase(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Actividad")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    duracion_minutos = models.IntegerField(default=60, verbose_name="Duración (Minutos)")
    activa = models.BooleanField(default=True, verbose_name="Activa")

    def __str__(self):
        return f"{self.nombre} ({self.duracion_minutos} min)"


class Sala(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre de la Sala")
    ubicacion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ubicación Interna")
    capacidad_maxima = models.IntegerField(verbose_name="Capacidad Máxima")
    activa = models.BooleanField(default=True, verbose_name="Habilitada")

    def __str__(self):
        return f"{self.nombre} - Capacidad: {self.capacidad_maxima}"


class Entrenador(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_entrenador',
        verbose_name="Usuario"
    )
    especialidad = models.CharField(max_length=100, blank=True, null=True, verbose_name="Especialidad")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - {self.especialidad or 'Entrenador'}"


class SesionClase(models.Model):
    ESTADOS = (
        ('PROGRAMADA', 'Programada'),
        ('EN_CURSO', 'En Curso'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    )

    tipo_clase = models.ForeignKey(TipoClase, on_delete=models.RESTRICT, related_name='sesiones', verbose_name="Actividad")
    entrenador = models.ForeignKey(Entrenador, on_delete=models.SET_NULL, null=True, blank=True, related_name='sesiones', verbose_name="Entrenador")
    sala = models.ForeignKey(Sala, on_delete=models.RESTRICT, related_name='sesiones', verbose_name="Sala")
    fecha = models.DateField(verbose_name="Fecha")
    hora_inicio = models.TimeField(verbose_name="Hora Inicio")
    hora_fin = models.TimeField(verbose_name="Hora Fin")
    cupo_maximo = models.IntegerField(verbose_name="Cupo Máximo")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROGRAMADA', verbose_name="Estado")

    def __str__(self):
        return f"{self.tipo_clase.nombre} — {self.fecha} ({self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')})"


class InscripcionClase(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='inscripciones_clase', verbose_name="Socio")
    sesion = models.ForeignKey(SesionClase, on_delete=models.CASCADE, related_name='inscritos', verbose_name="Sesión de Clase")
    fecha_inscripcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Inscripción")
    asistio = models.BooleanField(default=False, verbose_name="Asistió")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Registrado por"
    )

    class Meta:
        unique_together = ('socio', 'sesion')

    def __str__(self):
        return f"{self.socio.nombres} {self.socio.apellidos} en {self.sesion.tipo_clase.nombre}"