from django.db import models
from django.conf import settings
from socios.models import Socio

class Entrenador(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, verbose_name="Cuenta de Usuario")
    especialidad = models.CharField(max_length=100, verbose_name="Especialidad Principal")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción Profesional")

    def __str__(self):
        return f"Entrenador: {self.usuario.first_name} {self.usuario.last_name} ({self.especialidad})"


class AsignacionEntrenador(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='entrenadores_asignados', verbose_name="Socio")
    entrenador = models.ForeignKey(Entrenador, on_delete=models.CASCADE, related_name='socios_asignados', verbose_name="Entrenador")
    fecha_inicio = models.DateField(auto_now_add=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(blank=True, null=True, verbose_name="Fecha de Término")
    activa = models.BooleanField(default=True, verbose_name="Asignación Vigente")

    def __str__(self):
        return f"{self.socio.nombres} asignado a {self.entrenador.usuario.first_name}"