from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para los trabajadores de FitLife.
    Herenda de AbstractUser para conservar la seguridad de contraseñas y sesiones nativas de Django.
    """
    ROLES = (
        ('ADMINISTRADOR', 'Administrador'),
        ('RECEPCIONISTA', 'Recepcionista'),
        ('ENTRENADOR', 'Entrenador'),
    )

    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT Trabajador")
    rol = models.CharField(max_length=20, choices=ROLES, default='RECEPCIONISTA', verbose_name="Rol en el Sistema")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.rol}) - RUT: {self.rut}"