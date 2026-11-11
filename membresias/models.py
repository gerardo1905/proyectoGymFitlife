from django.db import models
from django.conf import settings
from socios.models import Socio

class Plan(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Plan")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    duracion_dias = models.IntegerField(verbose_name="Duración (Días)")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    activo = models.BooleanField(default=True, verbose_name="Disponible para Venta")

    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.duracion_dias} días)"


class Membresia(models.Model):
    ESTADOS = (
        ('ACTIVA', 'Activa'),
        ('VENCIDA', 'Vencida'),
        ('CONGELADA', 'Congelada'),
        ('CANCELADA', 'Cancelada'),
    )

    socio = models.ForeignKey(Socio, on_delete=models.RESTRICT, related_name='membresias', verbose_name="Socio")
    plan = models.ForeignKey(Plan, on_delete=models.RESTRICT, related_name='membresias', verbose_name="Plan Contratado")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Término")
    importe_acordado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Importe Acordado")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVA', verbose_name="Estado de Vigencia")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        verbose_name="Registrado por"
    )

    def __str__(self):
        return f"Membresía {self.socio.nombres} {self.socio.apellidos} — {self.estado}"


class Pago(models.Model):
    METODOS = (
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('DEBITO', 'Débito'),
        ('CREDITO', 'Crédito'),
    )

    membresia = models.ForeignKey(Membresia, on_delete=models.CASCADE, related_name='pagos', verbose_name="Membresía")
    usuario_responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Trabajador Responsable")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Pagado")
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Pago")
    metodo_pago = models.CharField(max_length=30, choices=METODOS, verbose_name="Método de Pago")
    comprobante_ref = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia/Nº Comprobante")

    def __str__(self):
        return f"Pago ${self.monto} - Membresía #{self.membresia.id}"


class IngresoGimnasio(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='ingresos', verbose_name="Socio")
    usuario_registro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, verbose_name="Validado por")
    fecha_hora_entrada = models.DateTimeField(auto_now_add=True, verbose_name="Hora de Entrada")
    fecha_hora_salida = models.DateTimeField(blank=True, null=True, verbose_name="Hora de Salida")

    def __str__(self):
        return f"Ingreso: {self.socio.nombres} - {self.fecha_hora_entrada.strftime('%Y-%m-%d %H:%M')}"