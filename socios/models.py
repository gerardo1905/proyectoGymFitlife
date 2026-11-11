from django.db import models
from django.conf import settings

class Socio(models.Model):
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT Socio")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=15, verbose_name="Teléfono")
    contacto_emergencia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contacto de Emergencia")
    fecha_registro = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")
    activo = models.BooleanField(default=True, verbose_name="Socio Activo")

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - RUT: {self.rut}"


class RegistroAcceso(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='accesos', verbose_name="Socio")
    fecha_hora_ingreso = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Ingreso")
    fecha_hora_salida = models.DateTimeField(null=True, blank=True, verbose_name="Fecha y Hora de Salida")
    permitido = models.BooleanField(default=True, verbose_name="Acceso Permitido")
    motivo_rechazo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Motivo de Rechazo")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Operador en Recepción"
    )

    class Meta:
        ordering = ['-fecha_hora_ingreso']

    def __str__(self):
        estado = "PERMITIDO" if self.permitido else f"RECHAZADO ({self.motivo_rechazo})"
        return f"{self.socio.nombres} - {estado} [{self.fecha_hora_ingreso.strftime('%d/%m/%Y %H:%M')}]"